

# эксперимент - что будет, если обрабатывать более крупными кусками (ничего интересного, всё то же самое)

# python merge_sentences.py gold/pattern.txt -o output/pattern.json -m 500

# разбиваем текстовый файл (образец с ручной разметкой) на предложения по строкам

python split_sentences_by_lines.py gold/pattern.txt -o output/pattern.json

# Добавляем пословную разметку

python extract_gold_accentuation.py output/pattern.json -o output/lib/GOLD_results.json

# размечаем ударения библиотекой ruaccent_turbo

python run_accentuator.py ruaccent_turbo output/lib/GOLD_results.json -o output/raw

# размечаем ударения библиотекой silero_stress

python run_accentuator.py silero_stress output/lib/GOLD_results.json -o output/raw

# размечаем ударения библиотекой accent_engine

python run_accentuator.py accent_engine output/lib/GOLD_results.json -o output/lib/

# размечаем ударения библиотекой llm_enhancer

# python run_accentuator.py llm_enhancer output/GOLD_results.json -o output/lib/

# размечаем ударения библиотекой wiki_enhancer

python run_accentuator.py wiki_enhancer output/lib/GOLD_results.json -o output/lib/

# Добавляем пословную разметку к результатам ruaccent_turbo

python extract_word_accentuation.py output/raw/ruaccent_turbo_results.json -o output/lib/ruaccent_turbo_results.json

# Добавляем пословную разметку к результатам silero_stress

python extract_word_accentuation.py output/raw/silero_stress_results.json -o output/lib/silero_stress_results.json

# Считаем ошибки

python compare_accentuators.py output/lib -o output/comparison.json

# Формируем отчет

python generate_report.py output/comparison.json output/report.md
