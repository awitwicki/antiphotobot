# antiphotobot
### Telegram bot which checks the image in chat for the fact that it is a photo of the monitor or screenshot.
![This is an image](.github/diagram.jpg)

[Live demo](https://awitwicki.github.io/deep-learning-examples/image-photo-classifier/)

Based on Aiogram and tensorflow
## Install

Use next environment variables:

* `ANTIPHOTOSBOT_TELEGRAM_TOKEN={YOUR_TOKEN}` - telegram token

    (other variables is not necessary and have default values)

* `ANTIPHOTOSBOT_ALLOWED_CHATS=-10010101,-10000101010` - whitelist chats. If it empty or not added to envs, whitelist mode will be turned off.

**Python:** Add to system environment that variables.

**Docker compose:**  create `.env` file and fill it with that variables.

## Run

### Docker compose

Then run in console command:

```
docker-compose up -d
```

### Python

```
cd app/
pip3 install -r requirements.txt
python main.py
```
