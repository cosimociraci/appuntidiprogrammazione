# app.py

import streamlit as st
import streamlit.components.v1 as components
from modules.pipeline_coordinator import PipelineCoordinator
import tempfile, os

st.set_page_config(page_title="Knowledge Mapper", layout="wide")
st.title("🧠 Local Knowledge Mapping Engine")

# Sidebar: configurazione modello
with st.sidebar:
    st.header("Configurazione")
    model_name = st.selectbox(
        "Modello LLM locale",
        ["mistral:7b-instruct", "llama3:8b-instruct", "qwen2:7b-instruct"],
        index=0
    )
    st.info("Assicurati che Ollama sia in esecuzione localmente sulla porta 11434.")

uploaded_file = st.file_uploader("Carica documento (PDF o Markdown)", type=["pdf", "md"])

if uploaded_file and st.button("🚀 Genera Mappa"):
    # Salvo il file in una temp dir per passare il path al loader
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=os.path.splitext(uploaded_file.name)[1]
    ) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(value: float, message: str):
        progress_bar.progress(value)
        status_text.text(message)

    try:
        coordinator = PipelineCoordinator(model_name=model_name)
        html_path = coordinator.run(tmp_path, progress_callback=update_progress)

        st.success("Mappa generata con successo!")
        
        # Embedding del grafo Pyvis direttamente nella pagina Streamlit
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=800, scrolling=False)

        # Download export
        with open(html_path, "rb") as f:
            st.download_button("⬇️ Scarica HTML", f, file_name="knowledge_map.html")

    except Exception as e:
        st.error(f"Errore durante la pipeline: {e}")
    finally:
        os.unlink(tmp_path)