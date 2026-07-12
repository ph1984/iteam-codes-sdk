"""JOB de exemplo: resume os pedidos dos ultimos N dias.

Roda isolado no seu projeto. Le parametros com get_input() e devolve com result().
Os recursos (datastore/kv) sao do projeto — sem credencial no codigo.
"""
from iteam import get_input, datastore, kv, result

inp = get_input()               # ex.: {"dias": 7}
dias = int(inp.get("dias", 7))

# Consulta o Data Store (ClickHouse) do projeto. Ajuste a tabela pro seu caso.
try:
    rows = datastore.query(
        f"SELECT count() AS total, sum(valor) AS receita "
        f"FROM pedidos WHERE data >= today() - {dias}"
    )
    total = rows[0].get("total", 0) if rows else 0
    receita = rows[0].get("receita", 0) if rows else 0
except Exception as e:
    # Sem Data Store alocado ainda? Devolve exemplo e explica.
    total, receita = 0, 0
    print(f"[aviso] sem Data Store/tabela: {e} — ative o Data Store na aba Codes pra dados reais.")

resumo = {"dias": dias, "pedidos": total, "receita": receita}
kv.set("ultimo_relatorio", resumo)     # guarda o ultimo resultado (estado por projeto)
print("Resumo:", resumo)
result(resumo)                          # saida estruturada do job
