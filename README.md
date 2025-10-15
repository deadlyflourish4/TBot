### Run with docker
```bash
git clone https://github.com/deadlyflourish4/TBot.git
cd TBot
docker build -t chatbot .
docker run -d -p 8000:8000 chatbot
```