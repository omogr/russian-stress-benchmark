

# эксперимент - что будет, если обрабатывать более крупными кусками (ничего интересного, всё то же самое)

# python merge_sentences.py src/GOLD_results.txt -o dst/pattern.json -m 500

# разбиваем текстовый файл (образец с ручной разметкой) на предложения по строкам

python split_sentences_by_lines.py src/GOLD_results.txt -o dst/pattern.json

# Добавляем пословную разметку

python extract_gold_accentuation.py dst/pattern.json -o dst/results/GOLD_results.json

# размечаем ударения библиотекой ruaccent_turbo

# python run_accentuator.py ruaccent_turbo dst/results/GOLD_results.json -o dst/tmp

# размечаем ударения библиотекой silero_stress

# python run_accentuator.py silero_stress dst/results/GOLD_results.json -o dst/tmp

# размечаем ударения библиотекой accent_engine

python run_accentuator.py accent_engine dst/results/GOLD_results.json -o dst/results/

# размечаем ударения библиотекой llm_enhancer

# python run_accentuator.py llm_enhancer dst/GOLD_results.json -o dst/results/

# размечаем ударения библиотекой wiki_enhancer

python run_accentuator.py wiki_enhancer dst/results/GOLD_results.json -o dst/results/

# Добавляем пословную разметку к результатам ruaccent_turbo

#python extract_word_accentuation.py dst/tmp/ruaccent_turbo_results.json -o dst/results/ruaccent_turbo_results.json

# Добавляем пословную разметку к результатам silero_stress

#python extract_word_accentuation.py dst/tmp/silero_stress_results.json -o dst/results/silero_stress_results.json

# Считаем ошибки

python compare_accentuators.py dst/results -o dst/comparison_results.json

# Формируем отчет

python generate_report.py dst/comparison_results.json dst/report.md
