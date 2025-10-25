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


## 앞으로 하고 싶은 남은 작업들(계속 추가될 예정)

- [ ] Datadog → Slack 알림 pipeline
- [ ] LLMOps용 Airflow DAG 추가  
- [ ] Kubernetes Helm Chart 버전 만들기  
- [ ] Streamlit + Grafana Embed로 인터랙티브 데모화 (gpt가하라는데 이것 못하게써요! 같이 할분이 있으면 이슈 올려 올려~)


---
![Compose](https://img.shields.io/badge/Docker-Compose-blue)
![LLM](https://img.shields.io/badge/LLM-LLaMA3.1-important)
![Tracing](https://img.shields.io/badge/Tracing-Datadog_%2B_Tempo-success)
![RAG](https://img.shields.io/badge/Pattern-RAG-green)
