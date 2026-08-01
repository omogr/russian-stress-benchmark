#!/usr/bin/env python3
"""
benchmark.py

Единый оркестратор для сравнения библиотек расстановки ударений.
Плагинная архитектура: адаптеры — минимальные модули с классом Accentuator,
общая логика (замер времени, нормализация, сохранение) — в runner.py.

Usage:
    # Инициализация
    python benchmark.py init

    # Полный прогон
    python benchmark.py run --gold gold/pattern.txt --config benchmark_config.json

    # Перезапуск конкретной библиотеки
    python benchmark.py run --gold gold/pattern.txt --libs silero_stress --force

    # Статус
    python benchmark.py status --gold gold/pattern.txt --config benchmark_config.json

    # Список адаптеров
    python benchmark.py list-adapters

    # Очистить кэш
    python benchmark.py clean --all
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_CACHE_DIR = Path(".benchmark_cache")
DEFAULT_CONFIG_FILE = Path("benchmark_config.json")
DEFAULT_ADAPTERS_DIR = Path("adapters")

RUNNER_SCRIPT = "runner.py"

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

@dataclass
class LibraryConfig:
    """Конфигурация одной библиотеки для тестирования."""
    name: str
    description: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "LibraryConfig":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            extra=data.get("extra", {}),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "extra": self.extra,
        }


@dataclass
class BenchmarkConfig:
    """Полная конфигурация бенчмарка."""
    libraries: List[LibraryConfig]
    output_dir: str = "output"
    cache_dir: str = ".benchmark_cache"
    adapters_dir: str = "adapters"
    dubious_file: Optional[str] = None
    reports: str = "both"

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkConfig":
        return cls(
            libraries=[LibraryConfig.from_dict(lib) for lib in data.get("libraries", [])],
            output_dir=data.get("output_dir", "output"),
            cache_dir=data.get("cache_dir", ".benchmark_cache"),
            adapters_dir=data.get("adapters_dir", "adapters"),
            dubious_file=data.get("dubious_file"),
            reports=data.get("reports", "both"),
        )

    def to_dict(self) -> dict:
        return {
            "libraries": [lib.to_dict() for lib in self.libraries],
            "output_dir": self.output_dir,
            "cache_dir": self.cache_dir,
            "adapters_dir": self.adapters_dir,
            "dubious_file": self.dubious_file,
            "reports": self.reports,
        }

    @classmethod
    def from_file(cls, path: Path) -> "BenchmarkConfig":
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_file(self, path: Path) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


# -----------------------------------------------------------------------------
# Adapter discovery
# -----------------------------------------------------------------------------

def discover_adapters(adapters_dir: Path) -> Dict[str, Path]:
    """Находит все адаптеры в директории (исключая runner.py и _*.py)."""
    adapters = {}
    if not adapters_dir.exists():
        return adapters

    for fpath in adapters_dir.glob("*.py"):
        fname = fpath.name
        if fname.startswith("_") or fname in ("runner.py", "__init__.py"):
            continue
        lib_name = fname[:-3]
        adapters[lib_name] = fpath

    return adapters


# -----------------------------------------------------------------------------
# Default config factory
# -----------------------------------------------------------------------------

def create_default_config() -> BenchmarkConfig:
    return BenchmarkConfig(
        libraries=[
            LibraryConfig(name="silero_stress", description="Silero stress placement"),
            LibraryConfig(name="udarenie", description="Udarenie with morphology"),
            LibraryConfig(name="accent_engine", description="Accent engine without morphology"),
        ],
        output_dir="output",
        cache_dir=".benchmark_cache",
        adapters_dir="adapters",
        dubious_file="gold/dubious.txt",
        reports="both",
    )


# -----------------------------------------------------------------------------
# Cache management
# -----------------------------------------------------------------------------

@dataclass
class CacheEntry:
    library_name: str
    gold_hash: str
    config_hash: str
    completed_at: str
    output_file: str
    result_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        return cls(**data)


class BenchmarkCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = cache_dir / "state.json"
        self.entries: Dict[str, CacheEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for name, entry_data in data.get("entries", {}).items():
                    self.entries[name] = CacheEntry.from_dict(entry_data)
            except (json.JSONDecodeError, KeyError):
                self.entries = {}

    def _save(self) -> None:
        data = {
            "version": 3,
            "updated_at": datetime.now().isoformat(),
            "entries": {name: entry.to_dict() for name, entry in self.entries.items()},
        }
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, library_name: str) -> Optional[CacheEntry]:
        return self.entries.get(library_name)

    def set(self, entry: CacheEntry) -> None:
        self.entries[entry.library_name] = entry
        self._save()

    def remove(self, library_name: str) -> bool:
        if library_name in self.entries:
            del self.entries[library_name]
            self._save()
            return True
        return False

    def clear_all(self) -> None:
        self.entries = {}
        self._save()

    def is_valid(self, library_name: str, gold_hash: str, config_hash: str) -> bool:
        entry = self.get(library_name)
        if entry is None:
            return False
        if entry.gold_hash != gold_hash or entry.config_hash != config_hash:
            return False
        result_path = Path(entry.output_file)
        if not result_path.exists():
            return False
        return True


def compute_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_string_hash(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


# -----------------------------------------------------------------------------
# Pipeline
# -----------------------------------------------------------------------------

class Pipeline:
    def __init__(self, config: BenchmarkConfig, gold_path: Path,
                 output_dir: Path, cache: BenchmarkCache,
                 force_libs: Optional[List[str]] = None,
                 verbose: bool = False):
        self.config = config
        self.gold_path = gold_path
        self.output_dir = output_dir
        self.cache = cache
        self.force_libs = set(force_libs or [])
        self.verbose = verbose
        self.adapters_dir = Path(config.adapters_dir)

        self.raw_dir = output_dir / "raw"
        self.lib_dir = output_dir / "lib"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.lib_dir.mkdir(parents=True, exist_ok=True)

        self.gold_hash = compute_file_hash(gold_path)
        self.config_hash = compute_string_hash(json.dumps(config.to_dict(), sort_keys=True))

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"[benchmark] {msg}")

    @staticmethod
    def _decode_output(data: bytes) -> str:
        if not data:
            return ""
        for enc in ('utf-8', 'cp1251', 'cp866', 'koi8-r', 'latin-1'):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode('utf-8', errors='replace')

    def run_command(self, cmd: List[str], description: str) -> int:
        self.log(f"Running: {' '.join(cmd)}")
        start = time.perf_counter()

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            result = subprocess.run(cmd, capture_output=True, text=False, env=env)
            elapsed = time.perf_counter() - start

            stdout = self._decode_output(result.stdout)
            stderr = self._decode_output(result.stderr)

            if result.returncode != 0:
                print(f"[ERROR] {description} failed (exit code {result.returncode})")
                if stderr:
                    print(f"  stderr: {stderr}")
                if stdout:
                    print(f"  stdout: {stdout}")
                return result.returncode

            self.log(f"{description} completed in {elapsed:.2f}s")
            if stdout:
                print(stdout, end='')
            return 0

        except FileNotFoundError as e:
            print(f"[ERROR] {description}: command not found — {e.filename}")
            return 1
        except PermissionError as e:
            print(f"[ERROR] {description}: permission denied — {e.filename}")
            return 1
        except Exception as e:
            print(f"[ERROR] {description} raised unexpected exception: {e}")
            traceback.print_exc()
            return 1

    def step_split(self) -> Path:
        output_path = self.raw_dir / "pattern.json"
        if output_path.exists():
            self.log(f"Reusing existing split: {output_path}")
            return output_path

        cmd = [
            sys.executable, "core/split_text_by_lines.py",
            str(self.gold_path), "-o", str(output_path),
        ]
        rc = self.run_command(cmd, "Split text into sentences")
        if rc != 0:
            raise RuntimeError("Split step failed")
        return output_path

    def step_extract_gold(self, split_path: Path) -> Path:
        output_path = self.lib_dir / "GOLD_results.json"
        dubious_arg = []
        if self.config.dubious_file and Path(self.config.dubious_file).exists():
            dubious_arg = ["-d", self.config.dubious_file]

        cmd = [
            sys.executable, "core/extract_accentuation.py",
            str(split_path), "-o", str(output_path),
            "--mode", "gold",
        ] + dubious_arg

        rc = self.run_command(cmd, "Extract GOLD accentuation")
        if rc != 0:
            raise RuntimeError("Gold extraction failed")
        return output_path

    def step_run_adapter0(self, lib_config: LibraryConfig, gold_json: Path) -> Path:
        """Запускает адаптер через runner.py."""
        raw_output = self.raw_dir / f"{lib_config.name}_results.json"

        # Формируем имя модуля для импорта.
        # Если адаптер лежит в adapters/<name>.py, то имя модуля — adapters.<name>
        module_name = f"adapters.{lib_config.name}"

        cmd = [
            sys.executable, RUNNER_SCRIPT,
            module_name,
            str(gold_json),
            str(raw_output),
        ]

        rc = self.run_command(cmd, f"Run adapter '{lib_config.name}'")
        if rc != 0:
            raise RuntimeError(f"Adapter '{lib_config.name}' failed")

        return raw_output

    def step_run_adapter(self, lib_config: LibraryConfig, gold_json: Path) -> Path:
        raw_output = self.raw_dir / f"{lib_config.name}_results.json"
        module_name = f"adapters.{lib_config.name}"

        cmd = [
            sys.executable, RUNNER_SCRIPT,
            module_name,
            str(gold_json),
            str(raw_output),
        ]

        # Запускаем без capture — вывод идёт прямо в терминал
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        print(f"Running: {' '.join(cmd)}")
        start = time.perf_counter()
        
        result = subprocess.run(cmd, stdout=None, stderr=None, env=env)
        
        elapsed = time.perf_counter() - start
        self.log(f"Adapter '{lib_config.name}' completed in {elapsed:.2f}s")

        if result.returncode != 0:
            raise RuntimeError(f"Adapter '{lib_config.name}' failed")
        return raw_output
    
    def step_extract_words(self, lib_config: LibraryConfig, raw_output: Path) -> Path:
        lib_output = self.lib_dir / f"{lib_config.name}_results.json"
        dubious_arg = []
        if self.config.dubious_file and Path(self.config.dubious_file).exists():
            dubious_arg = ["-d", self.config.dubious_file]

        cmd = [
            sys.executable, "core/extract_accentuation.py",
            str(raw_output), "-o", str(lib_output),
            "--mode", "lib", "--lib-name", lib_config.name,
        ] + dubious_arg

        rc = self.run_command(cmd, f"Extract words for '{lib_config.name}'")
        if rc != 0:
            raise RuntimeError(f"Word extraction for '{lib_config.name}' failed")
        return lib_output

    def step_compare(self) -> Path:
        output_path = self.output_dir / "comparison.json"
        cmd = [
            sys.executable, "core/compare_accentuators.py",
            str(self.lib_dir), "-o", str(output_path),
        ]
        rc = self.run_command(cmd, "Compare accentuators")
        if rc != 0:
            raise RuntimeError("Comparison failed")
        return output_path

    def step_report(self, comparison_path: Path) -> List[Path]:
        reports = []
        if self.config.reports in ("both", "ru"):
            ru_path = self.output_dir / "report.md"
            cmd = [sys.executable, "core/generate_report.py", str(comparison_path), str(ru_path)]
            if self.run_command(cmd, "Generate RU report") == 0:
                reports.append(ru_path)
        if self.config.reports in ("both", "en"):
            en_path = self.output_dir / "report_en.md"
            cmd = [sys.executable, "core/generate_report_en.py", str(comparison_path), str(en_path)]
            if self.run_command(cmd, "Generate EN report") == 0:
                reports.append(en_path)
        return reports

    def process_library(self, lib_config: LibraryConfig, gold_json: Path) -> Path:
        lib_output = self.lib_dir / f"{lib_config.name}_results.json"

        # Проверяем, что адаптер существует
        adapter_path = self.adapters_dir / f"{lib_config.name}.py"
        if not adapter_path.exists():
            print(f"[ERROR] Адаптер не найден: {adapter_path}")
            print(f"  Скопируйте adapters/_template.py → adapters/{lib_config.name}.py и настройте")
            raise RuntimeError(f"Adapter not found for '{lib_config.name}'")

        # Check cache
        needs_run = True
        if lib_config.name not in self.force_libs:
            if self.cache.is_valid(lib_config.name, self.gold_hash, self.config_hash):
                entry = self.cache.get(lib_config.name)
                if entry and Path(entry.output_file).exists():
                    self.log(f"Using cached results for '{lib_config.name}'")
                    needs_run = False
                    cached_path = Path(entry.output_file)
                    if cached_path != lib_output:
                        import shutil
                        shutil.copy2(cached_path, lib_output)

        if needs_run:
            print(f"\n{'='*60}")
            print(f"Processing library: {lib_config.name}")
            print(f"{'='*60}")

            raw_output = self.step_run_adapter(lib_config, gold_json)
            lib_output = self.step_extract_words(lib_config, raw_output)

            result_hash = compute_file_hash(lib_output)
            entry = CacheEntry(
                library_name=lib_config.name,
                gold_hash=self.gold_hash,
                config_hash=self.config_hash,
                completed_at=datetime.now().isoformat(),
                output_file=str(lib_output),
                result_hash=result_hash,
            )
            self.cache.set(entry)

        return lib_output

    def run(self) -> int:
        overall_start = time.perf_counter()
        try:
            print("\n" + "="*60)
            print("STEP 1: Split gold text into sentences")
            print("="*60)
            split_path = self.step_split()

            print("\n" + "="*60)
            print("STEP 2: Extract GOLD accentuation")
            print("="*60)
            gold_json = self.step_extract_gold(split_path)

            print("\n" + "="*60)
            print("STEP 3: Process libraries")
            print("="*60)
            for lib_config in self.config.libraries:
                self.process_library(lib_config, gold_json)

            print("\n" + "="*60)
            print("STEP 4: Compare results")
            print("="*60)
            comparison_path = self.step_compare()

            print("\n" + "="*60)
            print("STEP 5: Generate reports")
            print("="*60)
            report_paths = self.step_report(comparison_path)

            overall_time = time.perf_counter() - overall_start
            print("\n" + "="*60)
            print("BENCHMARK COMPLETE")
            print("="*60)
            print(f"Total time: {overall_time:.2f}s")
            print(f"Output directory: {self.output_dir}")
            print(f"Comparison: {comparison_path}")
            for rp in report_paths:
                print(f"Report: {rp}")
            print("="*60)
            return 0

        except RuntimeError as e:
            print(f"\n[ERROR] Pipeline failed: {e}")
            return 1
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            traceback.print_exc()
            return 1


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    gold_path = Path(args.gold)
    if not gold_path.exists():
        print(f"[ERROR] Gold file not found: {gold_path}")
        return 1

    config_path = Path(args.config) if args.config else DEFAULT_CONFIG_FILE
    if not config_path.exists():
        print(f"[ERROR] Config file not found: {config_path}")
        return 1

    config = BenchmarkConfig.from_file(config_path)
    cache = BenchmarkCache(Path(config.cache_dir))
    gold_hash = compute_file_hash(gold_path)
    config_hash = compute_string_hash(json.dumps(config.to_dict(), sort_keys=True))
    adapters_dir = Path(config.adapters_dir)
    discovered = discover_adapters(adapters_dir)

    print("\n" + "="*60)
    print("BENCHMARK STATUS")
    print("="*60)
    print(f"Gold file: {gold_path}")
    print(f"Gold hash: {gold_hash[:16]}...")
    print(f"Config: {config_path}")
    print(f"Config hash: {config_hash[:16]}...")
    print(f"Cache dir: {config.cache_dir}")
    print(f"Output dir: {config.output_dir}")
    print(f"Adapters dir: {config.adapters_dir}")
    if discovered:
        print(f"Discovered adapters: {', '.join(sorted(discovered.keys()))}")
    print("-"*60)
    print(f"{'Library':<20} {'Adapter':<10} {'Status':<15} {'Cached':<20}")
    print("-"*60)

    for lib in config.libraries:
        has_adapter = "✅" if lib.name in discovered else "❌"
        entry = cache.get(lib.name)
        if entry is None:
            status, cached = "NOT RUN", "—"
        elif entry.gold_hash != gold_hash:
            status, cached = "STALE (gold)", entry.completed_at[:19]
        elif entry.config_hash != config_hash:
            status, cached = "STALE (config)", entry.completed_at[:19]
        elif not Path(entry.output_file).exists():
            status, cached = "MISSING FILE", entry.completed_at[:19]
        else:
            status, cached = "VALID ✅", entry.completed_at[:19]
        print(f"{lib.name:<20} {has_adapter:<10} {status:<15} {cached:<20}")

    orphan = set(discovered.keys()) - {lib.name for lib in config.libraries}
    if orphan:
        print("-"*60)
        print(f"Orphan adapters (not in config): {', '.join(sorted(orphan))}")
    print("-"*60)
    print("STALE = результат устарел и будет пересчитан при следующем run")
    print("="*60)
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    cache_dir = Path(args.cache_dir) if args.cache_dir else DEFAULT_CACHE_DIR
    cache = BenchmarkCache(cache_dir)
    if args.all:
        cache.clear_all()
        print(f"Cache cleared: {cache_dir}")
        return 0
    if args.lib:
        removed = cache.remove(args.lib)
        print(f"Removed cache entry for: {args.lib}" if removed else f"No cache entry found for: {args.lib}")
        return 0
    print("Use --all to clear all cache, or --lib <name> to remove specific library")
    return 1


def cmd_run(args: argparse.Namespace) -> int:
    gold_path = Path(args.gold)
    if not gold_path.exists():
        print(f"[ERROR] Gold file not found: {gold_path}")
        return 1

    config_path = Path(args.config) if args.config else DEFAULT_CONFIG_FILE
    if config_path.exists():
        config = BenchmarkConfig.from_file(config_path)
        print(f"Loaded config: {config_path}")
    else:
        print(f"Config not found, creating default: {config_path}")
        config = create_default_config()
        config.to_file(config_path)
        print("Please review and edit benchmark_config.json, then run again.")
        return 0

    output_dir = Path(args.output_dir) if args.output_dir else Path(config.output_dir)
    cache_dir = Path(args.cache_dir) if args.cache_dir else Path(config.cache_dir)
    if args.reports:
        config.reports = args.reports

    if args.libs:
        lib_names = set(args.libs.split(','))
        config.libraries = [lib for lib in config.libraries if lib.name in lib_names]
        if not config.libraries:
            print("[ERROR] No matching libraries found in config")
            return 1

    cache = BenchmarkCache(cache_dir)
    force_libs = args.libs.split(',') if args.force and args.libs else None

    pipeline = Pipeline(
        config=config, gold_path=gold_path, output_dir=output_dir,
        cache=cache, force_libs=force_libs, verbose=args.verbose,
    )
    return pipeline.run()


def cmd_init(args: argparse.Namespace) -> int:
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG_FILE
    if config_path.exists() and not args.force:
        print(f"Config already exists: {config_path}")
        print("Use --force to overwrite")
        return 1

    config = create_default_config()
    config.to_file(config_path)
    print(f"Created default config: {config_path}")

    adapters_dir = Path(config.adapters_dir)
    adapters_dir.mkdir(parents=True, exist_ok=True)
    print(f"Adapters directory: {adapters_dir}")
    print("  Copy adapters/_template.py to <your_lib>.py and customize")
    return 0


def cmd_list_adapters(args: argparse.Namespace) -> int:
    adapters_dir = Path(args.adapters_dir) if args.adapters_dir else DEFAULT_ADAPTERS_DIR
    discovered = discover_adapters(adapters_dir)
    print("\n" + "="*60)
    print("DISCOVERED ADAPTERS")
    print("="*60)
    print(f"Adapters directory: {adapters_dir}")
    print("-"*60)
    if not discovered:
        print("No adapters found.")
        return 0
    for name in sorted(discovered.keys()):
        print(f"  {name:<25} {discovered[name]}")
    print("="*60)
    return 0


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Оркестратор бенчмарка расстановки ударений',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python benchmark.py init
  python benchmark.py run --gold gold/pattern.txt
  python benchmark.py run --gold gold/pattern.txt --libs silero_stress,udarenie
  python benchmark.py status --gold gold/pattern.txt
  python benchmark.py list-adapters
  python benchmark.py clean --all
        """,
    )
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')

    init_parser = subparsers.add_parser('init', help='Создать конфигурацию')
    init_parser.add_argument('-c', '--config', default='benchmark_config.json')
    init_parser.add_argument('--force', action='store_true')

    run_parser = subparsers.add_parser('run', help='Запустить бенчмарк')
    run_parser.add_argument('--gold', required=True)
    run_parser.add_argument('-c', '--config', default='benchmark_config.json')
    run_parser.add_argument('--libs')
    run_parser.add_argument('--force', action='store_true')
    run_parser.add_argument('-o', '--output-dir')
    run_parser.add_argument('--cache-dir')
    run_parser.add_argument('--reports', choices=['ru', 'en', 'both'])
    run_parser.add_argument('-v', '--verbose', action='store_true')

    status_parser = subparsers.add_parser('status', help='Показать статус')
    status_parser.add_argument('--gold', required=True)
    status_parser.add_argument('-c', '--config', default='benchmark_config.json')

    clean_parser = subparsers.add_parser('clean', help='Очистить кэш')
    clean_parser.add_argument('--all', action='store_true')
    clean_parser.add_argument('--lib')
    clean_parser.add_argument('--cache-dir')

    list_parser = subparsers.add_parser('list-adapters', help='Показать адаптеры')
    list_parser.add_argument('--adapters-dir', default='adapters')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    return {
        'init': cmd_init,
        'run': cmd_run,
        'status': cmd_status,
        'clean': cmd_clean,
        'list-adapters': cmd_list_adapters,
    }.get(args.command, lambda _: (parser.print_help(), 1)[1])(args)


if __name__ == '__main__':
    sys.exit(main())
