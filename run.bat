python split_text_by_lines.py gold/pattern.txt -o output/raw/pattern.json

python extract_gold_accentuation.py output/raw/pattern.json -o output/lib/GOLD_results.json -d dubious/dubious.txt

python run_accentuator.py silero_stress output/lib/GOLD_results.json -o output/raw

python run_accentuator.py udarenie output/lib/GOLD_results.json -o output/lib/ --data-path data_plus

python run_accentuator.py accent_engine output/lib/GOLD_results.json -o output/lib/ --data-path data_plus

python extract_word_accentuation.py output/raw/silero_stress_results.json -o output/test/silero_stress_results.json

python compare_accentuators.py output/lib -o output/comparison.json

python generate_report.py output/comparison.json output/report.md

