# datadog-llm-workshop
Datadog Summit Seoul 2025 (10/24)


## Intro

> “Datadog Summit 갔다가 충격받고 ,  
> 집에 오자마자 시작된 모니터링 SophieLabs.”
> LLM을 눈으로 보는 간단한 Workshop 정도의 프로젝트입니다!
> 제가 들은 WorkShop은 LLM Observability 입니다!  Datadog Learning Center에서 간단하게 해보실 수 있어요!


---

## 어떤 workshop project냐?!구여?

이건 “**AI가 어떻게 답을 만드는지를 눈으로 보는 볼 수있는 실험.실!**”이에요.  
대화형 AI가 문장을 만들 때, **어디에서 정보를 가져오고**,  
**얼마나 오래 걸리고**, **어디서 오류가 나는지**를  
Datadog과 Grafana를 이용해 한눈에 볼 수 있게 만드는 프로젝트라고 이해하면 될거 같아툐!

쉽게 말하면 
 "AI가 생각하는 과정을 CCTV처럼 지켜보는 시스템"이에요. 지켜보고 기사님께 고쳐주세요!! 요청 해야겠죠?!

- **Dash / Streamlit UI**로 질문을 던지면  
  → **RAG(검색 기반 AI)** 구조로 답변을 만들고  
  → **Datadog / Grafana / Loki / Tempo / Prometheus**에서  
     “AI의 flow + log + 속도 + cost”까지 한눈에 볼 수 있어요! 이런걸 관측 가능성 옵져바빌리티라고 합니다!

---

## 와! 그럼 어뜨케?!?!
> “AI가 대답하는 순간, 그 모든 과정을 Datadog과 Grafana가 기록한다.”

---

## 기술 요약 
| feature | desc |
|------|------|
|  **LLM Observability** | Model의 input/output, latenacy, error rate, used Token 등등 Tracingg |
|  **Loki + Promtail** | 로그를 자동 수집하고 Trace 연결( 이건 아직 못했거 사람 많은 곳 같다가 밤새서 했다니 몸살기운때문에 내일할게오) |
|  **Tempo + Datadog APM** | trace tada 병렬 수집 (multi backend) |
|  **Prometheus + Exemplars** | 요청 지연시간을 Trace ID와 함께 기록 |
|  **Dash / Streamlit UI** | 질문 입력 → 실시간 trace 확인 |
|  **RAG 구조** | 문서 검색 + LLM 결합형 답변 생성 | 

---


## 앞으로 남은 작업들(계속 추가될 예정)

- [ ] Datadog → Slack 알림 pipeline
- [ ] LLMOps용 Airflow DAG 추가  
- [ ] Kubernetes Helm Chart 버전 만들기  
- [ ] Streamlit + Grafana Embed로 인터랙티브 데모화 (gpt가하라는데 이것 못하게써요! 같이 할분이 있으면 이슈 올려 올려~)
---


##  올릴 곳이 없어서 올리는 후기 사진

<div align="center">

<img width="982" alt="Image" src="https://github.com/user-attachments/assets/5ca380ea-2b40-40e2-ab0a-6ef0bc5dd1eb" />
<img width="1454" alt="Image" src="https://github.com/user-attachments/assets/7fdb80ed-6fed-4f92-9e69-c2d228b7da16" />
<img width="600" alt="Image" src="https://github.com/user-attachments/assets/f0258eec-799c-41d5-bfc3-dc4986c433bc" />
<img width="600" alt="Image" src="https://github.com/user-attachments/assets/4b435127-85ed-4826-a67e-df9d1e914a10" />
<img width="600" alt="Image" src="https://github.com/user-attachments/assets/69338bf5-ec6b-40fe-a91b-945be6856ec9" />
<img width="600" alt="Image" src="https://github.com/user-attachments/assets/262351d9-aba9-45b4-9b99-0a19fb3d1740" />
<img width="600" alt="Image" src="https://github.com/user-attachments/assets/b685bea6-3dd8-4d86-b732-8fec4a6f5a49" />
<img width="600" alt="Image" src="https://github.com/user-attachments/assets/70376b33-931d-4d5c-8cde-6de8628f38e0" />
<img width="600" alt="Image" src="https://github.com/user-attachments/assets/c860a896-f186-4888-b44d-31f33eba4a77" />

</div>

---
## 🧩 Tech Stack

<p align="center">
  <img src="https://img.shields.io/badge/LLM-LLaMA3.1-ff69b4?style=for-the-badge&logo=meta&logoColor=white"/>
  <img src="https://img.shields.io/badge/RAG-Architecture-blue?style=for-the-badge&logo=OpenAI&logoColor=white"/>
  <img src="https://img.shields.io/badge/Datadog-Observability-purple?style=for-the-badge&logo=datadog&logoColor=white"/>
  <img src="https://img.shields.io/badge/Grafana-Tempo-orange?style=for-the-badge&logo=grafana&logoColor=white"/>
  <img src="https://img.shields.io/badge/Prometheus-Metrics-red?style=for-the-badge&logo=prometheus&logoColor=white"/>
  <img src="https://img.shields.io/badge/Loki-Logs-green?style=for-the-badge&logo=grafana&logoColor=white"/>
  <img src="https://img.shields.io/badge/OpenTelemetry-Tracing-00a3e0?style=for-the-badge&logo=opentelemetry&logoColor=white"/>
  <img src="https://img.shields.io/badge/Streamlit-UI-FE5E54?style=for-the-badge&logo=streamlit&logoColor=white"/>
  <img src="https://img.shields.io/badge/Dash-UI-008DE4?style=for-the-badge&logo=plotly&logoColor=white"/>
  <img src="https://img.shields.io/badge/Ollama-LocalLLM-1c1c1c?style=for-the-badge&logo=ollama&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
</p>
