### Run with docker
```bash
git clone https://github.com/deadlyflourish4/TBot.git
cd TBot
docker build -t chatbot .
docker run -d -p 8000:8000 chatbot
```

### Cloud run deployment
```bash
gclout auth login
gcloud auth configure-docker asia-docker.pkg.dev  

docker build -t chatbot . 
docker build -t asia-docker.pkg.dev/rare-karma-468001-k3/chatbot-guidepass/chatbot . 
docker tag chatbot asia-docker.pkg.dev/rare-karma-468001-k3/chatbot-guidepass/chatbot 
docker push asia-docker.pkg.dev/rare-karma-468001-k3/chatbot-guidepass/chatbot  
gcloud run deploy chatbot --image asia-docker.pkg.dev/rare-karma-468001-k3/chatbot-guidepass/chatbot:latest --region asia-southeast1 --allow-unauthenticated
```

### Work in Progress
1. problem with tts (edge-tts)
2. Need to update Database address
3. 