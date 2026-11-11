import os,hmac
from fastapi import FastAPI,Header,HTTPException
from pydantic import BaseModel,Field
from ai_service.classifier import predict

app=FastAPI(title='宿修故障分类服务',version='1.0.0')
class TextInput(BaseModel):
    text:str=Field(min_length=5,max_length=2000)

@app.get('/health')
def health():return {'status':'ok'}

@app.post('/predict')
def classify(data:TextInput,x_service_token:str=Header(default='')):
    expected=os.getenv('AI_SERVICE_TOKEN','')
    if not expected or not hmac.compare_digest(expected,x_service_token):raise HTTPException(401,'invalid service token')
    return predict(data.text)
