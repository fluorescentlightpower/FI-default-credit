Credit Default Prediction Service

Описание

Проект представляет собой production-like сервис машинного обучения для прогнозирования дефолта по кредитным картам. Используется датасет UCI Credit Card (Тайвань). Реализован полный цикл:

обучение модели с использованием метода случайного леса (RandomForestClassifier, scikit-learn)
сохранение модели
веб-сервис для инференса
асинхронная обработка пакетных запросов через RabbitMQ
контейнеризация и оркестрация (Docker, docker-compose)
proxy через nginx + uWSGI

Поддерживаются два режима работы:

синхронный прогноз для единичного запроса (/predict)
асинхронный прогноз для пакетного запроса (/predict_batch) через очередь

Архитектура

Выбрана микросервисная архитектура, так как она позволяет изолировать разные задачи - синхронные и асинхронные запросы. Также каждый сервис отвечает за отдельный участок работы (API, входной трафик, обработка очереди, управление сообщениями). Выше отказоустойчивость (при остановке worker можно делать единичные /predict). Микросервисную архитектуру проще будет масштабировать.

nginx принимает HTTP-запросы и проксирует их в ml_service (uWSGI + Flask).
ml_service обрабатывает асинхронные запросы и отправляет задачи для пакетной обработки во входную очередь RabbitMQ. Брокер сообщений также может использоваться для масштабирования (например, добавления новых сервисов, базы данных и т. д., которые будут использовать очереди сообщений совместно)
worker слушает очередь, выполняет инференс и отправляет результаты в очередь результатов.

Структура репозитория:
/app - основное приложение сервиса
/docker - конфигурационный файл для nginx
/models - модель в формате pickle и скрипт обучения модели
/notebooks - Jupyter Notebook с базовым отображением параметров обучающих данных
/src - функции подготовки данных и собственно вызова инференса
/worker - обработчик сообщений в очередях при асинхронном инференсе

Возможно использование ELK-стека:

Контейнеры пишут структурированные JSON-логи в stdout.
Filebeat собирает логи docker.
Logstash парсит и нормализует поля.
Elasticsearch хранит логи.
Kibana показывает дашборды и предоставляет поиск.

Основные компоненты для сервиса:

ml_service (Flask + uWSGI)
worker (обработка очереди)
rabbitmq (брокер сообщений)
nginx (reverse proxy)

Запуск

Локально (без Docker)

Создать виртуальное окружение:

python3 -m venv .venv
source .venv/bin/activate

Установить зависимости:

pip install -r requirements.txt

Обучить модель:

python models/train_model.py

Запустить API:

python -m app.app

Сервис будет доступен на:

http://localhost:5000

Для работы batch-режима локально необходимо отдельно поднять RabbitMQ.

Запуск в Docker

Ссылка на репозиторий Docker Hub:

https://hub.docker.com/repository/docker/fluorescent1800/fi_default_credit/tags/1.0/sha256-846d8da6bb7fedfedd88a6daf62d9ab4f56c4b7d638bc89d342dc9a0c5c2295b

Присутствуют файлы Dockerfile и docker-compose.yml.
Убедиться, что установлен Docker и Docker Compose.
Запустить сервисы:

docker compose up --build

Проверить, что сервисы запущены:

docker compose ps

Должны быть запущены ml-service, nginx, worker, rabbitmq

Доступные endpoints:

API: http://localhost:5000
RabbitMQ UI: http://localhost:15672
 (пользователь guest / пароль guest)

Остановка:

docker compose down

Примеры запросов

Проверка работоспособности (метод GET)

curl http://localhost:5000/health

Ожидаемый ответ:

{"status":"ok"}

Синхронный прогноз (один объект, POST)

curl -X POST http://localhost:5000/predict

-H "Content-Type: application/json"
-d '{
"LIMIT_BAL": 20000,
"SEX": 2,
"EDUCATION": 2,
"MARRIAGE": 1,
"AGE": 24,
"PAY_0": 2,
"PAY_2": 2,
"PAY_3": -1,
"PAY_4": -1,
"PAY_5": -2,
"PAY_6": -2,
"BILL_AMT1": 3913,
"BILL_AMT2": 3102,
"BILL_AMT3": 689,
"BILL_AMT4": 0,
"BILL_AMT5": 0,
"BILL_AMT6": 0,
"PAY_AMT1": 0,
"PAY_AMT2": 689,
"PAY_AMT3": 0,
"PAY_AMT4": 0,
"PAY_AMT5": 0,
"PAY_AMT6": 0
}'

Ответ:

{
"prediction": 1,
"probability": 0.81
}

Асинхронный пакетный прогноз (POST, содержимое каждого объекта аналогично запросу для синхронного прогноза)

curl -X POST http://localhost:5000/predict_batch

-H "Content-Type: application/json"
-d '[
{ ... объект 1 ... },
{ ... объект 2 ... }
]'

Ответ:

{
"status": "accepted",
"items_count": 2
}

Результаты асинхронной обработки

Результаты не возвращаются напрямую в HTTP-ответе. Они отправляются worker в очередь batch_predictions_results RabbitMQ

Просмотр логов:

docker compose logs -f worker

Результат пакетного прогноза можно посмотреть через RabbitMQ UI:

http://localhost:15672

Queues → batch_predictions_results

Формат запросов и ответов

Формат входного JSON для /predict

JSON-объект с признаками клиента:

{ объект }

Названия и форматы полей:

LIMIT_BAL (int)
SEX (int)
EDUCATION (int)
MARRIAGE (int)
AGE (int)
PAY_0, PAY_2 ... PAY_6 (int)
BILL_AMT1 ... BILL_AMT6 (float)
PAY_AMT1 ... PAY_AMT6 (float)

Все поля обязательны и должны соответствовать обучающей выборке. Соответствие наименований полей признаков проверяется. При несовпадении будет ошибка

Формат ответа /predict

{
"prediction": 0 или 1,
"probability": float
}

Формат запроса /predict_batch

Список JSON-объектов:

[
{ объект 1 },
{ объект 2 },
...
]

Формат сообщения в очереди результатов

{
"status": "processed",
"items_count": int,
"results": [
{
"prediction": int,
"probability": float
},
{
"prediction": int,
"probability": float
},
...
]
}

Примечания

Порядок признаков сохраняется из обучающей выборки
Модель загружается из pickle
Асинхронная обработка реализована через RabbitMQ
Для надежности используется ручное подтверждение обработки сообщений (ack) в worker

Модель можно преобразовать в формат ONNX-ML для оптимизации.
Среда инференса может быть легче и быстрее, чем полноценный scikit-learn. ONNX Runtime часто требует меньше RAM для вычисления предсказаний небольших моделей. Для преобразования используется skl2onnx примерно следующим образом:

import pickle
import numpy as np
from skl2onnx import to_onnx

with open(MODEL_PATH, "rb") as f:
    artifact = pickle.load(f)

model = artifact["model"]
features = artifact["features"]

initial_input = np.zeros((1, n_features), dtype=np.float32)

onnx_model = to_onnx(
    model,
    initial_input,
    target_opset=12
)

onnx_model можно сериализовать и использовать без загрузки Python-объекта sklearn



Для управления версиями данных и управления экспериментами могут использоваться инструменты DVC и MLflow

DVC (Data Version Control)

Назначение - управлять версиями данных и артефактов модели так же, как Git управляет кодом.

В контексте проекта:

фиксирует версии исходного набора данных
фиксирует промежуточные данные (feature engineering, train/test split)
хранит версии обученных моделей (model_v1.pkl, model_v2.pkl, ...)
позволяет воспроизводить обучение - модель получена из этих данных этим кодом

MLflow

Назначение - отслеживание экспериментов и управление версиями моделей.

В контексте проекта:

логирует параметры модели (n_estimators, class_weight и т.д.)
логирует метрики (accuracy, f1, ROC AUC)
хранит версии моделей как эксперименты
позволяет сравнивать модели (v1, v2, ...)
может использоваться как реестр моделей

Метрики

При обучении модели оцениваются метрики ROC AUC, Accuracy, F1.
Также для интерпретации бизнес-пользователями можно оценивать долю просрочек (дефолтов) среди клиентов, которым выдали кредит, и прибыль (доход от клиентов минус потери от просрочек)

Долю просрочек можно рассчитать через предсказания модели:
вероятности - y_proba = model.predict_proba(X_test)[:, 1]
пусть порог отсечения threshold = 0.4
если вероятность дефолта >= 0.4 - отказать
если вероятность дефолта < 0.4  - одобрить
approved = y_proba < threshold
default_rate = y_test[approved].mean() - в среднем дефолт среди одобренных

Прибыль рассчитывается также по прогнозам

profit = (
    ((y_test[approved] == 0).sum() * profit_good)
    -
    ((y_test[approved] == 1).sum() * loss_default)
)

где

profit_good = 1000 - прибыль с хорошего клиента
loss_default = 5000 - потеря с дефолтного клиента