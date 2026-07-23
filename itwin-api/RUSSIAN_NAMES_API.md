# API для работы с русскими названиями колонок

## Обзор

API теперь поддерживает работу с русскими названиями колонок базы данных. Это позволяет получать локализованные названия полей и их описания для лучшего понимания данных пользователями.

## Новые Endpoints

### 1. Получить все русские названия

**GET** `/russian-names`

Возвращает все доступные русские названия колонок, сгруппированные по таблицам.

**Ответ:**
```json
{
  "data": {
    "heatpipesections": {
      "diameterinternal": ["Диаметр внутренний, мм", "описание поля"],
      "wallthickness": ["Толщина стенки, мм", "описание поля"]
    },
    "nodes": {
      "externalcodeid": ["Код расчетной схемы", "описание поля"]
    }
  }
}
```

### 2. Получить русские названия для таблицы

**GET** `/russian-names/{table}`

Возвращает русские названия колонок для указанной таблицы. **Поиск без учета регистра.**

**Параметры:**
- `table` (string) - название таблицы

**Примеры:**
- `/russian-names/heatpipesections`
- `/russian-names/HEATPIPESECTIONS`
- `/russian-names/HeatPipeSections`

**Ответ:**
```json
{
  "table": "heatpipesections",
  "data": {
    "diameterinternal": ["Диаметр внутренний, мм", "описание поля"],
    "wallthickness": ["Толщина стенки, мм", "описание поля"]
  }
}
```

### 3. Получить русское название для колонки

**GET** `/russian-names/column/{column}`

Возвращает русское название и описание для указанной колонки. **Поиск без учета регистра.**

**Параметры:**
- `column` (string) - название колонки в формате `table|column` или просто `column`

**Примеры:**
- `/russian-names/column/heatpipesections|diameterinternal`
- `/russian-names/column/HEATPIPESECTIONS|DIAMETERINTERNAL`
- `/russian-names/column/HeatPipeSections|DiameterInternal`
- `/russian-names/column/diameterinternal`
- `/russian-names/column/DIAMETERINTERNAL`

**Ответ:**
```json
{
  "column": "heatpipesections|diameterinternal",
  "russian_name": "Диаметр внутренний, мм",
  "description": "«Внутренний диаметр» - цифровое поле, значение которого определяет внутренний диаметр труб..."
}
```


## Модифицированные Endpoints

### 1. Получить данные линейного объекта

**GET** `/line/{table}/{id}?include_russian_names=true`

**Новый параметр:**
- `include_russian_names` (boolean, по умолчанию `false`) - включить русские названия в ответ

**Пример ответа с русскими названиями:**
```json
{
  "data": {
    "tabs": [
      {
        "title": "Общая информация",
        "subsections": [
          {
            "title": "Параметры трубы",
            "fields": [
              {
                "table": "heatpipesections",
                "field": "diameterinternal",
                "label": "Диаметр внутренний, мм",
                "russian_name": "Диаметр внутренний, мм",
                "description": "«Внутренний диаметр» - цифровое поле...",
                "value": 150,
                "type": "text"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### 2. Получить данные точечного объекта

**GET** `/node/{table}/{id}?include_russian_names=true`

**Новый параметр:**
- `include_russian_names` (boolean, по умолчанию `false`) - включить русские названия в ответ

## Использование

### Включение русских названий в существующие запросы

Чтобы получить русские названия вместе с данными объекта, добавьте параметр `include_russian_names=true`:

```bash
# Получить данные линейного объекта с русскими названиями
GET /line/heatpipesections/123?include_russian_names=true

# Получить данные точечного объекта с русскими названиями  
GET /node/nodes/456?include_russian_names=true
```

### Получение только русских названий

```bash
# Все русские названия
GET /russian-names

# Русские названия для конкретной таблицы (без учета регистра)
GET /russian-names/heatpipesections
GET /russian-names/HEATPIPESECTIONS
GET /russian-names/HeatPipeSections

# Русское название для конкретной колонки (без учета регистра)
GET /russian-names/column/heatpipesections|diameterinternal
GET /russian-names/column/HEATPIPESECTIONS|DIAMETERINTERNAL
GET /russian-names/column/HeatPipeSections|DiameterInternal

```

## Обработка ошибок

- **503 Service Unavailable** - если русские названия не инициализированы
- **500 Internal Server Error** - при ошибках загрузки или обработки данных

## Инициализация

Русские названия автоматически инициализируются при запуске приложения из файлов:
- `rus_names/gid.txt1`
- `rus_names/gid.txt2` 
- `rus_names/gid.txt3`
- `rus_names/gid.txt4`

Если инициализация не удалась, endpoints будут возвращать ошибку 503.
