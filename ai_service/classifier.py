import json
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import classification_report,confusion_matrix,accuracy_score
from ai_service.dataset import dataset

MODEL=Path(__file__).parent/'model.joblib'
VERSION='char-tfidf-logreg-v1'

def train():
    rows=dataset()
    train_rows=[r for r in rows if r['split']=='train']
    model=make_pipeline(TfidfVectorizer(analyzer='char',ngram_range=(1,3),sublinear_tf=True),LogisticRegression(C=8,max_iter=1000,random_state=42))
    model.fit([r['text'] for r in train_rows],[r['label'] for r in train_rows])
    joblib.dump(model,MODEL)
    metrics={'model_version':VERSION,'data_source':'人工编写的模拟故障；同一故障的4种模板改写仅位于同一集合；不代表真实校园泛化能力。','total_samples':len(rows),'train_samples':len(train_rows),'evaluations':{}}
    for split in ['validation','test']:
        selected=[r for r in rows if r['split']==split]
        y=[r['label'] for r in selected];pred=model.predict([r['text'] for r in selected])
        labels=list(model.classes_)
        metrics['evaluations'][split]={'samples':len(y),'accuracy':accuracy_score(y,pred),'report':classification_report(y,pred,output_dict=True,zero_division=0),'labels':labels,'confusion_matrix':confusion_matrix(y,pred,labels=labels).tolist()}
    Path('docs').mkdir(exist_ok=True)
    Path('docs/ai-metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    Path('ai_service/dataset.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
    return model,metrics

_model=None
def predict(text):
    global _model
    if _model is None:
        _model=joblib.load(MODEL) if MODEL.exists() else train()[0]
    scores=_model.predict_proba([text])[0];i=int(scores.argmax())
    return {'category':str(_model.classes_[i]),'confidence':float(scores[i]),'model_version':VERSION}

if __name__=='__main__':
    _,metrics=train()
    print(json.dumps(metrics,ensure_ascii=False,indent=2))
