# AiDetectionFrontend

Фронтенд приложение для детекции ИИ-сгенерированного текста.

## Рекомендуемая IDE

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (отключите Vetur).

## Настройка проекта

```sh
npm install
```

### Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```env
VITE_API_KEY=your-api-key-here
VITE_API_BASE_URL=https://158.160.53.90
```

### Разработка

```sh
npm run dev
```

### Сборка для продакшена

```sh
npm run build
```

### Линтинг

```sh
npm run lint
```

## Технологии

- Vue 3 + TypeScript
- Vite
- PrimeVue
- Tailwind CSS
- Pinia

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).
