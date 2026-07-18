# ER-диаграмма данных

## Что показано

Диаграмма отражает все таблицы, которые реально описаны в SQLAlchemy-моделях backend:

- `users` - пользователи системы;
- `groups` - учебные группы;
- `detection` - основная история проверок и результаты анализа текста;
- `user_detections` - дополнительная привязка проверки к пользователю, исходной проверке и учебному контексту;
- `plagiarism_checks` - отчеты проверки на совпадения;
- `plagiarism_corpus` - документы, добавленные в корпус антиплагиата;
- `text_fragments` - фрагменты текста для сравнения по шинглам и SimHash.

## Важные упрощения

- Отдельной таблицы `documents` в коде нет. Документ представлен записью `detection`: имя файла, тип файла, извлеченный текст и результат анализа.
- Подозрительные AI-фрагменты не вынесены в отдельную таблицу. Они хранятся внутри `full_response` / `windows` как JSON.
- Похожие документы антиплагиата хранятся в `similar_documents_json`, а не в отдельной таблице.
- `users.group_id`, `detection.user_id` и `plagiarism_checks.user_id` допускают `NULL`, поэтому на диаграмме связи с группой/пользователем отмечены как опциональные: запись может быть без группы или без привязанного пользователя.
- Связи построены по реальным `ForeignKey`: `users.group_id`, `detection.user_id`, `user_detections.user_id`, `user_detections.original_detection_id`, `plagiarism_checks.detection_id`, `plagiarism_checks.user_id`, `plagiarism_corpus.detection_id`, `text_fragments.detection_id`.

## Нормальная форма

После добавления `ForeignKey` для `user_detections.original_detection_id` основные сущности и связи приведены к структуре не ниже третьей нормальной формы: группы, пользователи, проверки, привязки пользователя, корпус антиплагиата и фрагменты вынесены в отдельные таблицы, а неключевые поля зависят от ключей своих таблиц.

В коде остаются осознанные денормализованные поля для хранения готового результата внешних проверок: `detection.full_response`, `plagiarism_checks.matches_json`, `plagiarism_checks.similar_documents_json`, а также снимок `plagiarism_checks.filename`. Для строгой физической 3НФ их можно вынести в отдельные таблицы, но для текущей системы они используются как сохраненный отчет/снимок результата.

## Файлы-источники

- `AiDetectionBackend/core/database.py`
- `AiDetectionBackend/core/user_database.py`
- `AiDetectionBackend/services/detection_service.py`
- `AiDetectionBackend/plagiarism_engine.py`
