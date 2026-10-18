# BionicPRO — Спринт 9

В PR представлены оба задания спринта: архитектура безопасности и PKCE, а также сервис пользовательских отчётов.

| Задание | Материалы |
|---|---|
| 1. Безопасность и PKCE | [`Task1/README_Task1.md`](Task1/README_Task1.md), [`Task1/BionicPRO_Task1_TO_BE.drawio`](Task1/BionicPRO_Task1_TO_BE.drawio) |
| 2. Отчёты, Airflow, ClickHouse, API и UI | [`Task2/README.md`](Task2/README.md), [`Task2/Architecture_C4/BionicPRO_Task2.drawio`](Task2/Architecture_C4/BionicPRO_Task2.drawio) |

## Локальный запуск задания 2

```bash
docker compose -f Task2/docker-compose.yaml up --build -d
```

После запуска: интерфейс — http://localhost:3000, Airflow — http://localhost:8081, Swagger API — http://localhost:8000/docs.

Подробные команды и тестовые сценарии см. в `Task2/README.md`.
