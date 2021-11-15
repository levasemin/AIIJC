# nlp-witnesses

Запускаете markers.py с файлом april_data.csv, он создает файл stats_all.csv

Запускаете markers.py с файлом train_v4.csv, он создает файл stats_all_train.csv

Запускаете add_columns, он создает файлы merged_data_client.csv, merged_data_driver.csv (надо будет поменять в функции целевой столбец)

Запускаете final_note, он создает V_rate.csv

Запускаете prepeare_comment.ipynb, происходит обработка коммента и получение K_rate

Запускаете recalc_rank.py, он печатает датафрейм с K_rank, V_rank
