# QuestLog

## Table of Contents

- [Getting Started](#getting-started)

## Getting Started

1. Clone the repo
2. Copy the environment files and update or complete the values:

    ```bash
      cp .env.example .env
      cp backend/.env.example backend/.env
      cp frontend/.env.local.example frontend/.env.local
    ```

3. Build and start the Docker containers:

    ```bash
      docker compose up --build
    ```

4. Run migrations:

    ```bash
      docker compose exec backend python manage.py migrate
    ```

## Subsequent runs

```bash
docker compose up
```

## Accessing Services

postgreSQL Shell:

```bash
docker compose exec db psql -U your_username -d your_database
```

OR

```bash
psql -h localhost -p 5432 -U your_username -d your_database
```

Redis CLI:

```bash
docker compose exec redis redis-cli -a your_password
```

OR

```bash
redis-cli -h localhost -p 6379 -a your_password
```

Django GUI: `http://localhost:8000`

Django Shell:

```bash
docker compose exec backend python manage.py <command>
```

 OR

```bash
docker compose exec backend django-admin <command>
```
