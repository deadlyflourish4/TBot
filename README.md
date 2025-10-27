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
docker build -t asia-docker.pkg.dev/guidepassasiacloud/guidepassasiachatbot/chatbot . 
docker tag chatbot asia-docker.pkg.dev/guidepassasiacloud/guidepassasiachatbot/chatbot 
docker push asia-docker.pkg.dev/guidepassasiacloud/guidepassasiachatbot/chatbot  
gcloud run deploy chatbot ^
  --image asia-docker.pkg.dev/guidepassasiacloud/guidepassasiachatbot/chatbot:latest ^
  --region=asia-southeast1 ^
  --platform=managed ^
  --set-env-vars STATIC_TOKEN="470dce3ef7229267af60319f5079d5f99d6121e371e1823d028d1d170c9463ef" ^
  --allow-unauthenticated
```

### Work in Progress
1. problem with tts (edge-tts)
2. Need to update Database address
3. 