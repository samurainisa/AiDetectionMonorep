# Контрибьютинг

## Стиль коммитов — Conventional Commits

История проекта ведётся в формате
[Conventional Commits](https://www.conventionalcommits.org/). Это делает лог
читаемым и позволяет автоматически генерировать changelog.

```
<type>(<scope>): <краткое описание в нижнем регистре>

[необязательное тело]

[необязательный футер]
```

### Типы

| Тип        | Когда использовать                                       |
|------------|----------------------------------------------------------|
| `feat`     | Новая функциональность                                   |
| `fix`      | Исправление бага                                         |
| `docs`     | Только документация                                      |
| `style`    | Форматирование без изменения логики                      |
| `refactor` | Рефакторинг без новых фич и фиксов                       |
| `perf`     | Улучшение производительности                             |
| `test`     | Тесты                                                    |
| `build`    | Сборка, зависимости                                      |
| `ci`       | CI/CD конфигурация                                       |
| `chore`    | Рутина, не влияющая на код приложения                    |

### Scope

Указывайте область изменения: `backend`, `frontend`, `deploy`, `db`, `auth`,
`plagiarism`, `ci` и т.д.

### Примеры

```
feat(frontend): add plagiarism report export button
fix(backend): handle empty text in /analyze-text
docs(deploy): describe DNS setup for ai-detection.ru
chore(deps): bump primevue to 4.3.5
```

## Ветки

- `main` — стабильная, готовая к деплою ветка.
- Работа ведётся в ветках `feat/...`, `fix/...`, `chore/...` и вливается через
  Pull Request.

## Перед коммитом

- Frontend: `npm run lint && npm run type-check`
- Не коммитьте секреты: `.env` и реальные ключи в `.gitignore`.
- Окончания строк нормализуются автоматически (`.gitattributes`, LF).
