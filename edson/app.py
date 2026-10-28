import os
import pandas as pd
import streamlit as st

ARQUIVO = "orcamentos.csv"
COLUNAS = [
    "id", "cliente", "servico", "status", "valor_cobrado",
    "pecas_previstas", "mao_obra_prevista", "outros_previstos",
    "pecas_reais", "mao_obra_real", "outros_reais", "observacoes"
]

st.set_page_config(page_title="OrçaFácil | Dashboard", page_icon="📊", layout="wide")

def carregar_dados():
    if not os.path.exists(ARQUIVO):
        pd.DataFrame(columns=COLUNAS).to_csv(
            ARQUIVO, index=False, sep=";", encoding="utf-8-sig"
        )
    try:
        df = pd.read_csv(ARQUIVO, sep=";", encoding="utf-8-sig")
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        df = pd.DataFrame(columns=COLUNAS)
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = 0 if col in [
                "id", "valor_cobrado", "pecas_previstas", "mao_obra_prevista",
                "outros_previstos", "pecas_reais", "mao_obra_real", "outros_reais"
            ] else ""
    for col in [
        "valor_cobrado", "pecas_previstas", "mao_obra_prevista", "outros_previstos",
        "pecas_reais", "mao_obra_real", "outros_reais"
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    return df[COLUNAS]

def salvar_dados(df):
    df[COLUNAS].to_csv(ARQUIVO, index=False, sep=";", encoding="utf-8-sig")

def calcular(df):
    df = df.copy()
    df["custo_previsto"] = df["pecas_previstas"] + df["mao_obra_prevista"] + df["outros_previstos"]
    df["custo_real"] = df["pecas_reais"] + df["mao_obra_real"] + df["outros_reais"]
    df["lucro_previsto"] = df["valor_cobrado"] - df["custo_previsto"]
    df["resultado_atual"] = df["valor_cobrado"] - df["custo_real"]
    df["variacao_custos"] = df["custo_real"] - df["custo_previsto"]
    return df

def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("OrçaFácil — Dashboard de Orçamentos")
st.caption("Controle de serviços, peças, mão de obra e alertas de lucro ou prejuízo.")

df = calcular(carregar_dados())

with st.sidebar:
    st.header("Filtros")
    statuses = ["Todos"] + sorted([x for x in df["status"].dropna().astype(str).unique() if x])
    filtro_status = st.selectbox("Status do serviço", statuses)
    busca = st.text_input("Buscar cliente ou serviço").strip().lower()

visao = df.copy()
if filtro_status != "Todos":
    visao = visao[visao["status"].astype(str) == filtro_status]
if busca:
    visao = visao[
        visao["cliente"].astype(str).str.lower().str.contains(busca, na=False)
        | visao["servico"].astype(str).str.lower().str.contains(busca, na=False)
    ]

total_cobrado = visao["valor_cobrado"].sum()
custo_real = visao["custo_real"].sum()
resultado = visao["resultado_atual"].sum()
em_prejuizo = int((visao["resultado_atual"] < 0).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Orçamentos", len(visao))
c2.metric("Total a receber", moeda(total_cobrado))
c3.metric("Custos reais", moeda(custo_real))
c4.metric("Resultado atual", moeda(resultado), delta="Saldo positivo" if resultado >= 0 else "Atenção: prejuízo", delta_color="normal" if resultado >= 0 else "inverse")

if em_prejuizo:
    st.error(f"ALERTA: {em_prejuizo} serviço(s) está(ão) com prejuízo no momento. Revise os custos ou negocie uma alteração no orçamento.")
elif len(visao):
    st.success("Nenhum serviço desta seleção está com prejuízo neste momento.")

tab1, tab2, tab3 = st.tabs(["Visão geral", "Cadastrar orçamento", "Atualizar custos"])

with tab1:
    st.subheader("Acompanhamento dos serviços")
    if visao.empty:
        st.info("Nenhum orçamento encontrado com esses filtros.")
    else:
        tabela = visao[[
            "id", "cliente", "servico", "status", "valor_cobrado",
            "custo_previsto", "custo_real", "lucro_previsto", "resultado_atual"
        ]].copy()
        tabela.columns = [
            "ID", "Cliente", "Serviço", "Status", "Valor cobrado",
            "Custo previsto", "Custo real", "Lucro previsto", "Resultado atual"
        ]
        st.dataframe(tabela, use_container_width=True, hide_index=True)
        st.subheader("Valor cobrado x custos reais")
        grafico = visao.set_index("cliente")[["valor_cobrado", "custo_real"]]
        grafico.columns = ["Valor cobrado", "Custos reais"]
        st.bar_chart(grafico)
        st.subheader("Resultado por serviço")
        resultados = visao.set_index("cliente")[["resultado_atual"]].rename(columns={"resultado_atual": "Lucro / prejuízo"})
        st.bar_chart(resultados)
        prejuizos = visao[visao["resultado_atual"] < 0]
        if not prejuizos.empty:
            st.markdown("#### Serviços que precisam de atenção")
            for _, r in prejuizos.iterrows():
                st.warning(
                    f"#{int(r['id'])} — {r['cliente']} ({r['servico']}): "
                    f"prejuízo de {moeda(abs(r['resultado_atual']))}."
                )

with tab2:
    st.subheader("Cadastrar novo orçamento")
    with st.form("novo_orcamento", clear_on_submit=True):
        cliente = st.text_input("Nome do cliente")
        servico = st.text_input("Descrição do serviço")
        status = st.selectbox("Status", ["Orçamento", "Aprovado", "Em andamento", "Concluído", "Cancelado"])
        valor_cobrado = st.number_input("Valor combinado com o cliente (R$)", min_value=0.0, step=10.0)
        a, b, c = st.columns(3)
        pecas_previstas = a.number_input("Peças previstas (R$)", min_value=0.0, step=10.0)
        mao_obra_prevista = b.number_input("Mão de obra prevista (R$)", min_value=0.0, step=10.0)
        outros_previstos = c.number_input("Outros custos previstos (R$)", min_value=0.0, step=10.0)
        observacoes = st.text_area("Observações")
        enviado = st.form_submit_button("Salvar orçamento")
        if enviado:
            if not cliente.strip() or not servico.strip():
                st.error("Preencha o nome do cliente e a descrição do serviço.")
            else:
                atual = carregar_dados()
                novo_id = int(atual["id"].max()) + 1 if not atual.empty else 1
                novo = {
                    "id": novo_id, "cliente": cliente.strip(), "servico": servico.strip(),
                    "status": status, "valor_cobrado": valor_cobrado,
                    "pecas_previstas": pecas_previstas, "mao_obra_prevista": mao_obra_prevista,
                    "outros_previstos": outros_previstos, "pecas_reais": 0.0,
                    "mao_obra_real": 0.0, "outros_reais": 0.0, "observacoes": observacoes.strip()
                }
                atual = pd.concat([atual, pd.DataFrame([novo])], ignore_index=True)
                salvar_dados(atual)
                st.success(f"Orçamento #{novo_id} cadastrado!")
                st.rerun()

with tab3:
    st.subheader("Atualizar custos reais")
    base = carregar_dados()
    if base.empty:
        st.info("Cadastre um orçamento primeiro.")
    else:
        opcoes = {
            f"#{int(r['id'])} — {r['cliente']} | {r['servico']}": int(r["id"])
            for _, r in base.iterrows()
        }
        escolhido = st.selectbox("Selecione o serviço", list(opcoes.keys()))
        id_escolhido = opcoes[escolhido]
        registro = base[base["id"] == id_escolhido].iloc[0]
        with st.form("atualizar_custos"):
            st.write(f"**Valor cobrado:** {moeda(registro['valor_cobrado'])}")
            a, b, c = st.columns(3)
            pecas_reais = a.number_input("Gasto real com peças (R$)", min_value=0.0, value=float(registro["pecas_reais"]), step=10.0)
            mao_obra_real = b.number_input("Custo real da mão de obra (R$)", min_value=0.0, value=float(registro["mao_obra_real"]), step=10.0)
            outros_reais = c.number_input("Outros gastos reais (R$)", min_value=0.0, value=float(registro["outros_reais"]), step=10.0)
            novo_status = st.selectbox(
                "Status atualizado", ["Orçamento", "Aprovado", "Em andamento", "Concluído", "Cancelado"],
                index=["Orçamento", "Aprovado", "Em andamento", "Concluído", "Cancelado"].index(registro["status"])
                if registro["status"] in ["Orçamento", "Aprovado", "Em andamento", "Concluído", "Cancelado"] else 2
            )
            novas_obs = st.text_area("Observações", value=str(registro["observacoes"]))
            atualizado = st.form_submit_button("Atualizar serviço")
            if atualizado:
                base.loc[base["id"] == id_escolhido, "pecas_reais"] = pecas_reais
                base.loc[base["id"] == id_escolhido, "mao_obra_real"] = mao_obra_real
                base.loc[base["id"] == id_escolhido, "outros_reais"] = outros_reais
                base.loc[base["id"] == id_escolhido, "status"] = novo_status
                base.loc[base["id"] == id_escolhido, "observacoes"] = novas_obs.strip()
                salvar_dados(base)
                st.success("Custos atualizados com sucesso!")
                st.rerun()

st.divider()
st.caption("Os dados ficam salvos localmente no arquivo orcamentos.csv. Faça cópias de segurança regularmente.")
