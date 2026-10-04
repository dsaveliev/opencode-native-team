# Spec: opencode-native-team

## Objective

**Продуктизация паттерна native×4 combined v5** — мультиагентной команды разработки
на чистых примитивах opencode, без единой строчки TypeScript-кода фреймворка.

Пользователь — инженер, использующий opencode (или любую совместимую консоль) для
автоматизации разработки. Успех — команда ставится копированием 5 файлов в
`.opencode/agents/` проекта и сразу работает: план → код → тесты → ревью → коммиты.

Пять файлов. Ноль зависимостей. Ноль vendor-lock. Полный контроль.

## Tech Stack

- **runtime**: opencode ≥ 1.18 (agents, Task tool, permissions)
- **агенты**: markdown + YAML frontmatter (mode, permission, temperature)
- **процесс**: OpenSpec (CLI ≥ 1.14, `openspec new change` → `validate` → `archive`)
- **дисциплина**: agent-skills (25 скиллов Addy Osmani, глобальная установка)
- **модели**: любые через opencode; рекомендованный роутинг:
  - coder, reviewer, orchestrator → основная модель (glm-5.3)
  - planner, tester → лёгкая модель (glm-5.3-flash)
- **код проекта**: не зависит от языка команды (универсальные контракты)

## Commands

```bash
# Установка в проект
./install.sh /path/to/project        # копирует agents/ в .opencode/agents/

# Проверка после установки
cd /path/to/project && ls .opencode/agents/
# → orchestrator.md planner.md coder.md tester.md reviewer.md

# Запуск (в каталоге проекта)
opencode run --agent orchestrator 'Прочитай TASK.md и выполни задание полностью.'
```

## Project Structure

```
opencode-native-team/
  README.md                    — обзор, quick start, философия
  SPEC.md                      — этот файл (спека проекта)
  LICENSE                      — MIT
  
  agents/                      — ядро: 5 контрактов команды
    orchestrator.md            — тимлид v5: openspec-цикл + скилл-mapping + evidence-[x]
    planner.md                 — анализ/декомпозиция (read-only)
    coder.md                   — реализация (TDD-дисциплина)
    tester.md                  — тесты (main-тестируемость + гонки)
    reviewer.md                — ревью-вердикты (5 осей, read-only, t=0,1)
  
  install.sh                   — установка в целевой проект
  
  docs/
    design-decisions.md        — 13 проектных решений паттерна (из bake-off)
    v4-to-v5.md                — что изменилось и почему (по результатам серии)
    timing-analysis.md         — декомпозиция времени v4, причины 81 мин
  
  examples/
    TASK.md                    — канонический пример задания (sliding-counter)
    judge.sh                   — детерминированный судья (для верификации команды)
```

## Code Style

Контракты агентов — markdown с YAML frontmatter:

```yaml
---
description: Тимлид — оркестрация команды разработки по openspec-циклу
mode: primary
permission:
  task:
    "*": "deny"
    "planner": "allow"
    "coder": "allow"
    "tester": "allow"
    "reviewer": "allow"
---
```

Тело — на русском (или языке команды), сухо, структурно, без воды.
Каждый контракт ≤ 60 строк (v5-предел; v1 был ~20, v4 ~40).

## Testing Strategy

- **Детерминированный судья** (`examples/judge.sh`) — независимая проверка результата
- **openspec validate** — валидность change-артефактов после каждого коммита
- **Evidence-based `[x]`** — каждая отметка в tasks.md обязана содержать команду + результат
- Прогон на эталонном TASK.md (sliding-counter) — сквозная проверка команды

## Boundaries

**Always:**
- Все артефакты — только внутри репозитория проекта
- `[x]` — только с доказательством (команда + результат)
- Fail-loud: сбой скилла/CLI → фиксация в DECISIONS.md → retry/обход
- Атомарный коммит = одна задача (с task-номером в сообщении)
- После каждого коммита — openspec validate

**Ask first:**
- Изменение контрактов агентов (это ядро паттерна)
- Добавление новых ролей
- Смена модельного роутинга

**Never:**
- Код плагина / TypeScript (философия: контракты, не код)
- Внешние state-каталоги (`~/.anything`) — только внутри проекта
- Удаление данных на NAS или в любых хранилищах
- Секреты в артефактах

## Success Criteria

1. `install.sh` копирует 5 файлов — команда готова к работе за < 1 мин
2. На эталонном TASK.md команда v5 даёт: judge 15/15, покрытие > 90 %,
   main > 70 %, ≤ 55 мин, ≤ 450 k input, 0 вмешательств оператора
3. Контракты читаются человеком за 5 минут (все 5 файлов)
4. Изменение контракта (например, добавить роль) — правкой одного файла

## Open Questions

1. Нужен ли тонкий плагин для авто-гейтов (openspec validate hook) — или судья/CI достаточно?
2. Публиковать на GitHub (публичное) или держать приватным в ~/Sync/Repo?
3. Версионировать как semver (v5.0.0) или git-тегами (v5)?
