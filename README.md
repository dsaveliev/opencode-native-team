# opencode-native-team

Мультиагентная команда разработки на чистых примитивах opencode.
**5 markdown-файлов. Ноль зависимостей. Ноль vendor-lock.**

```
план → код → тесты → ревью → коммиты
```

## Философия

**Контракт вместо кода.** Каждый агент — это должностная инструкция (markdown),
а не программа. Поведение порождается текстом контракта + правами инструментов.

Продуктизация паттерна, победившего в [bake-off мультиагентных команд](https://github.com/dsatov/Atlas/tree/main/labs/agent-bakeoff):
лучшая экономия (344–521 k input против 5,6 M у Swarm), ноль вмешательств
оператора, judge 15/15.

## Quick Start

```bash
# 1. Установка в ваш проект
./install.sh /path/to/your/project

# 2. Запуск команды
cd /path/to/your/project
opencode run --agent orchestrator 'Прочитай TASK.md и выполни задание полностью.'
```

## Состав команды

| Роль | Права | Температура | Модель |
|---|---|---|---|
| orchestrator | primary; task → 4 роли; git commit | default | основная |
| planner | read-only | default | flash |
| coder | edit + bash | default | основная |
| tester | edit + bash | default | flash |
| reviewer | read-only (git + go test) | **0,1** | основная |

## Слои дисциплины

```
Процесс (openspec)     → «в каком порядке договариваемся»
Дисциплина (skills)    → «как делать каждый вид работы»
Команда (эти агенты)   → «кто что делает»
```

V5 включает mapping-таблицу: какой скилл на каком этапе openspec — прямо в контракт
оркестратора. Никакой неопределённости.

## Документация

- [SPEC.md](SPEC.md) — спека проекта
- [docs/design-decisions.md](docs/design-decisions.md) — 13 проектных решений
- [docs/v4-to-v5.md](docs/v4-to-v5.md) — эволюция и что изменилось
- [docs/timing-analysis.md](docs/timing-analysis.md) — почему v4 занял 81 мин

## Origin

Рождён в [Atlas labs/agent-bakeoff](https://github.com/dsatov/Atlas/tree/main/labs/agent-bakeoff)
в ходе сравнительной обкатки трёх фреймворков (Native · FlowDeck · Swarm) и серии
native×4 (barebone · skills · openspec · combined).

## License

MIT
