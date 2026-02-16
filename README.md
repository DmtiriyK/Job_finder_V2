# Job Finder - Automated German Remote Job Scraper

Автоматизированный scraper для поиска удаленных вакансий в Германии с интеллектуальной системой скоринга.

## 📋 Возможности

- **Автоматический сбор вакансий** из 5 источников (RemoteOK, We Work Remotely, Arbeitnow, Germany Remote Jobs, LinkedIn)
- **Интеллектуальный скоринг** (100-балльная система):
  - TF-IDF similarity (40 баллов) - семантическое соответствие профилю
  - Tech stack matching (30 баллов) - соответствие технологий
  - Remote priority (15 баллов) - приоритет полностью удаленной работы
  - Keywords (10 баллов) - ключевые слова и требования
  - Contract type (5 баллов) - тип контракта
- **Извлечение технологий** с FlashText (O(n) производительность)
- **Дедупликация** на основе SHA256 хешей
- **Экспорт результатов** в Google Sheets, Telegram и JSON
- **Полное покрытие тестами** с pytest

## 🚀 Быстрый старт

### 1. Установка зависимостей

```powershell
# Полная установка (с spaCy и dev инструментами)
pip install -r requirements-full.txt

# Или облегченная версия для CI/CD
pip install -r requirements-light.txt
```

### 2. Настройка окружения

```powershell
# Скопируйте пример конфигурации
Copy-Item .env.example .env

# Отредактируйте .env под ваши нужды
notepad .env
```

### 3. Настройте профиль

Отредактируйте `config/profile.yaml` с вашими навыками и предпочтениями:

```yaml
name: "Your Name"
roles:
  - "Backend Developer"
  - "Full Stack Developer"

skills:
  languages:
    - name: "C#"
      experience_years: 5
      proficiency: "Expert"
    - name: "Python"
      experience_years: 3
      proficiency: "Advanced"

preferences:
  remote: "100%"
  locations:
    - "Berlin"
    - "München"
    - "Remote"
  contract_types:
    - "Festanstellung"
    - "Freiberuflich"
  min_score: 65

profile_text: |
  Experienced backend developer with 5+ years of C# and .NET experience.
  Strong focus on cloud-native applications with Docker and Kubernetes.
```

### 4. Запустите scraper

```powershell
# Запустить все scrapers
python main.py

# Запустить конкретный scraper
python main.py --sources remoteok

# Сохранить результаты в файл
python main.py --output results.json

# Отправить в Google Sheets
python main.py --export-sheets
```

## 📁 Структура проекта

```
Job_finder/
├── config/                     # Конфигурация
│   ├── settings.py            # Настройки приложения
│   ├── profile.yaml           # Профиль пользователя
│   ├── scoring_rules.yaml     # Правила скоринга
│   └── tech_dictionary.json   # Словарь технологий
├── models/                     # Pydantic модели
│   ├── job.py                 # Job, ScoreResult
│   └── profile.py             # Profile, Skill
├── utils/                      # Утилиты
│   ├── logger.py              # Структурное логирование
│   └── rate_limiter.py        # Ограничение частоты запросов
├── cache/                      # Кеширование
│   └── manager.py             # Менеджер кеша (diskcache + joblib)
├── scrapers/                   # Scrapers для разных источников
│   ├── base.py                # Базовый класс
│   ├── remoteok.py            # RemoteOK scraper (RSS)
│   ├── wwr.py                 # We Work Remotely
│   ├── arbeitnow.py           # Arbeitnow
│   ├── germany_remote.py      # Germany Remote Jobs
│   └── linkedin.py            # LinkedIn (Playwright)
├── extractors/                 # Извлечение данных
│   └── tech_extractor.py      # Извлечение технологий (FlashText)
├── matchers/                   # Сопоставление
│   └── tfidf_matcher.py       # TF-IDF similarity
├── scorers/                    # Скоринг
│   ├── scorer.py              # Главный scorer
│   └── components/            # Компоненты скоринга
│       ├── tfidf_scorer.py
│       ├── tech_scorer.py
│       ├── remote_scorer.py
│       ├── keyword_scorer.py
│       └── contract_scorer.py
├── processors/                 # Обработка результатов
│   └── deduplicator.py        # Дедупликация
├── integrations/               # Внешние интеграции
│   ├── google_sheets.py       # Google Sheets экспорт
│   └── telegram.py            # Telegram уведомления
├── tests/                      # Тесты
│   ├── conftest.py            # Pytest fixtures
│   ├── test_config.py         # Тесты конфигурации
│   └── test_models.py         # Тесты моделей
├── requirements-light.txt      # Облегченные зависимости (~500MB)
├── requirements-full.txt       # Полные зависимости (~800MB)
├── .env.example               # Пример конфигурации
├── IMPLEMENTATION_PLAN.md     # План реализации
└── MILESTONES.md              # Milestones разбивка
```

## 🧪 Тестирование

```powershell
# Запустить все тесты
pytest

# С покрытием
pytest --cov=. --cov-report=html

# Конкретный тест
pytest tests/test_models.py -v

# С подробным выводом
pytest -vv -s
```

## 📊 Система скоринга

### Компоненты (100 баллов)

1. **TF-IDF Similarity (40 баллов)**: Семантическое соответствие описания вакансии вашему профилю
2. **Tech Stack (30 баллов)**: Соответствие требуемых технологий вашим навыкам
3. **Remote Type (15 баллов)**: Приоритет полностью удаленной работы
4. **Keywords (10 баллов)**: Релевантные ключевые слова и требования
5. **Contract Type (5 баллов)**: Предпочитаемый тип контракта

### Формулы нормализации

```python
# TF-IDF: 0.0-1.0 → 0-40 баллов
tfidf_score = cosine_similarity * 40

# Tech Stack: количество совпадений → 0-30 баллов
tech_score = min(matched_count * 2.5, 30)

# Remote: категориальная оценка
remote_score = {
    "Remote": 15,
    "Hybrid (1-2 дня)": 12,
    "Hybrid (3+ дня)": 8,
    "Onsite": 0
}
```

## 🔧 Конфигурация

### Переменные окружения (.env)

- `LOG_LEVEL`: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
- `CACHE_ENABLED`: Включить кеширование (true/false)
- `MIN_SCORE`: Минимальный Score для фильтрации (0-100)
- `MAX_CONCURRENT_REQUESTS`: Макс. одновременных запросов
- `REQUEST_DELAY_SECONDS`: Задержка между запросами

### Scoring Rules (config/scoring_rules.yaml)

Настройте веса для технологий, ключевых слов и фильтров:

```yaml
tech_stack:
  high_priority:
    - name: "C#"
      points: 5
    - name: ".NET"
      points: 5
  
  negative:
    - name: "SAP"
      points: -3
```

### Tech Dictionary (config/tech_dictionary.json)

500+ технологических терминов в 15 категориях для извлечения:

- Languages (C#, Python, TypeScript, ...)
- Frameworks (.NET, React, Django, ...)
- Databases (PostgreSQL, MongoDB, ...)
- Cloud (AWS, Azure, GCP, ...)
- DevOps (Docker, Kubernetes, ...)
- И многое другое...

## 📈 Прогресс разработки

### ✅ Milestone 1: Foundation & Infrastructure (ЗАВЕРШЕНО)
- [x] Структура проекта
- [x] Конфигурационная система
- [x] Pydantic модели
- [x] Утилиты (logger, rate limiter, cache)
- [x] Базовые тесты

### 🔄 Milestone 2: First Scraper Working (В ПРОЦЕССЕ)
- [ ] Базовый класс scraper
- [ ] RemoteOK scraper (RSS)
- [ ] Tech extractor
- [ ] End-to-end тест

### ⏳ Следующие Milestones
- Milestone 3: All Scrapers
- Milestone 4: TF-IDF Matcher
- Milestone 5: Complete Scoring System
- Milestone 6: Deduplication & Caching
- Milestone 7: Export & Integrations
- Milestone 8: CLI & Main Pipeline
- Milestone 9: Testing & Optimization

## 🤝 Вклад

Этот проект следует плану реализации в `IMPLEMENTATION_PLAN.md` и структуре milestones в `MILESTONES.md`.

## 📄 Лицензия

MIT License

## 🔗 Источники вакансий

1. **RemoteOK** - RSS feed с удаленными вакансиями
2. **We Work Remotely** - HTML scraping
3. **Arbeitnow** - RSS feed германских вакансий
4. **Germany Remote Jobs** - HTML scraping
5. **LinkedIn** - Playwright (JavaScript rendering)

## 📞 Контакты

Для вопросов и предложений создайте Issue.
