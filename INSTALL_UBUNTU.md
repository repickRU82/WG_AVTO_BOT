# Установка и запуск WG_AVTO_BOT на Ubuntu (22.04/24.04)

Ниже приведена пошаговая инструкция для **MVP-версии** бота (aiogram + PostgreSQL + Redis + WireGuard config generation + MikroTik API skeleton).

---

## 1) Подготовка сервера

```bash
sudo apt update
sudo apt install -y git curl ca-certificates gnupg lsb-release
sudo apt install -y python3 python3-venv python3-pip python3-dev build-essential libffi-dev libssl-dev
sudo apt install -y postgresql postgresql-contrib redis-server
```

Проверить версии:

```bash
python3 --version
psql --version
redis-server --version
```

---

## 2) Клонирование проекта

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> WG_AVTO_BOT
sudo chown -R "$USER":"$USER" /opt/WG_AVTO_BOT
cd /opt/WG_AVTO_BOT
```

---

## 3) Настройка PostgreSQL

Войти под postgres-пользователем:

```bash
sudo -u postgres psql
```

Создать БД и пользователя (в psql):

```sql
CREATE USER wg_bot WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
CREATE DATABASE wg_bot OWNER wg_bot;
GRANT ALL PRIVILEGES ON DATABASE wg_bot TO wg_bot;
\q
```

Проверка подключения:

```bash
psql "postgresql://wg_bot:CHANGE_ME_STRONG_PASSWORD@127.0.0.1:5432/wg_bot" -c "SELECT 1;"
```

---

## 4) Настройка Redis

Включить и запустить:

```bash
sudo systemctl enable redis-server
sudo systemctl restart redis-server
sudo systemctl status redis-server --no-pager
```

Проверка:

```bash
redis-cli ping
```

Ожидается ответ `PONG`.

---

## 5) Python-окружение и зависимости

```bash
cd /opt/WG_AVTO_BOT
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

Проверка, что зависимости импортируются:

```bash
python -c "import aiogram, asyncpg, redis, bcrypt, cryptography, librouteros; print('ok')"
```

---

## 6) Настройка переменных окружения

Создать `.env` на основе примера:

```bash
cp .env.example .env
```

Отредактировать:

```bash
nano .env
```

Минимально обязательно заполнить:

- `BOT_TOKEN`
- `ADMIN_TELEGRAM_IDS`
- `DATABASE_DSN`
- `REDIS_DSN`
- `WG_SERVER_PUBLIC_KEY`
- `WG_ENDPOINT_HOST`
- `WG_ENDPOINT_PORT`
- `MIKROTIK_HOST`, `MIKROTIK_USERNAME`, `MIKROTIK_PASSWORD`, `MIKROTIK_USE_TLS`, `WG_INTERFACE_NAME`


Рекомендуемые значения для RouterOS API:

```dotenv
WG_INTERFACE_NAME=WG-Users
WG_NETWORK_CIDR=10.66.66.0/24
MIKROTIK_PORT=8728
MIKROTIK_USE_TLS=false
```

Для безопасности ограничьте доступ к API на MikroTik только IP-адресом сервера бота:

```routeros
/ip service set api address=192.168.5.17/32 port=8728
```

Если включаете TLS (`MIKROTIK_USE_TLS=true`) с self-signed сертификатом, бот может работать в insecure-режиме (`MIKROTIK_TLS_INSECURE=true`, verify=CERT_NONE). Для strict TLS используйте доверенный сертификат и `MIKROTIK_TLS_INSECURE=false`.

Пример DSN для локального PostgreSQL/Redis:

```dotenv
DATABASE_DSN=postgresql://wg_bot:CHANGE_ME_STRONG_PASSWORD@127.0.0.1:5432/wg_bot
REDIS_DSN=redis://127.0.0.1:6379/0
```

---

## 7) Первый запуск (инициализация схемы + polling)

```bash
cd /opt/WG_AVTO_BOT
source .venv/bin/activate
python -m app.main
```

При первом старте бот автоматически создаёт таблицы MVP:

- `users`
- `wireguard_configs`
- `subscriptions`
- `logs`

Остановить: `Ctrl+C`.

---

## 8) Проверка в Telegram

1. Откройте чат с ботом.
2. Выполните `/start`.
3. Задайте PIN (4-10 цифр).
4. Выполните `/login` и введите PIN.
5. Выполните `/menu`.
6. Выполните `/new_connection` — бот должен выдать WG-конфиг.
7. Выполните `/my_connections`.

---

## 9) Автозапуск через systemd

Создать unit-файл:

```bash
sudo nano /etc/systemd/system/wg-avto-bot.service
```

Содержимое:

```ini
[Unit]
Description=WG AVTO Telegram Bot
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=<YOUR_LINUX_USER>
WorkingDirectory=/opt/WG_AVTO_BOT
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/WG_AVTO_BOT/.venv/bin/python -m app.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Активировать сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable wg-avto-bot
sudo systemctl start wg-avto-bot
sudo systemctl status wg-avto-bot --no-pager
```

Логи:

```bash
journalctl -u wg-avto-bot -f
```

---

## 10) Запуск через Docker Compose (альтернатива)

Требуется установленный Docker + Compose plugin.

```bash
cd /opt/WG_AVTO_BOT
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f bot
```

Остановка:

```bash
docker compose down
```

---

## 11) Базовая безопасность (рекомендации)

1. Используйте сложные пароли для PostgreSQL и MikroTik API.
2. Откройте только необходимые порты в firewall.
3. Запретите публичный доступ к PostgreSQL и Redis, если не требуется.
4. Добавьте регулярный backup базы:

```bash
pg_dump "postgresql://wg_bot:CHANGE_ME_STRONG_PASSWORD@127.0.0.1:5432/wg_bot" > /opt/WG_AVTO_BOT/backup_$(date +%F).sql
```

5. Используйте отдельного пользователя в MikroTik с минимально нужными правами.

---

## 12) Диагностика проблем

### Бот не стартует из-за env
Проверьте наличие обязательных переменных:

```bash
grep -E '^(BOT_TOKEN|DATABASE_DSN|REDIS_DSN|WG_SERVER_PUBLIC_KEY)=' .env
```

### Ошибка подключения к PostgreSQL

```bash
sudo systemctl status postgresql --no-pager
psql "postgresql://wg_bot:CHANGE_ME_STRONG_PASSWORD@127.0.0.1:5432/wg_bot" -c "SELECT NOW();"
```

### Ошибка подключения к Redis

```bash
sudo systemctl status redis-server --no-pager
redis-cli -h 127.0.0.1 -p 6379 ping
```

### Ошибка MikroTik API
Проверьте адрес/порт и TLS-флаг (`8728` без TLS, `8729` с TLS), а также API user/password в `.env`. Если раньше использовался нестандартный порт (например `25`), верните RouterOS API на `8728`.

