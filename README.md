# MM-KISS-Bot

Market Making - Super Simple bot

## Steps, to run localy

### 1. Clone your fork of this repository

```bash
git clone https://github.com/username/MM-KISS-Bot
```

### 2. Set environment variables

Rename `example.env` to `.env` with this command: `mv example.env .env` and put your variables here

### 3. Start project with [docker](https://docs.docker.com)

1) [Install Docker](https://docs.docker.com/engine/install/) (if not already installed)
2) Start Docker
3) Build image

```bash
docker build --tag "mm-bot" .
```

4) Run container

```bash
docker run mm-bot
```
