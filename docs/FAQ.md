# FAQ — perguntas comuns (usuário leigo)

**Preciso saber programar?**
Não. Você descreve em português no Claude/Cursor; a IA escreve, testa e publica. Você só aprova e usa o link.

**Onde pego a chave do projeto?**
No iTeam: seu projeto → aba **Codes** → **"Copiar prompt pro Claude"** (já vem com o ID do projeto e a chave).
Cole no Claude dentro desta pasta.

**Qual a diferença entre Job, Serviço e Artefato?**
- **Job** = roda e termina (relatório, importação). Pode ser agendado.
- **Serviço** = uma **API** que fica no ar (endpoints GET/POST…).
- **Artefato** = **telas** (React) que ficam no ar; podem consumir a sua API.
Veja [../README.md](../README.md) e a pasta [../examples](../examples).

**Quero "um sisteminha". O que peço?**
Peça **uma API (serviço)** com os dados/ações + **um artefato (telas)** que mostra e opera esses dados.
A IA cria os dois e conecta.

**Quem consegue abrir o que eu criei?**
Por padrão, só **membros do projeto** (logados no iTeam). Você pode deixar público se quiser.

**Dá pra outra empresa/sistema usar minha API?**
Sim, mandando o **token do usuário iTeam** no header `X-Iteam-Token`. Sem token válido de membro, é bloqueado.

**As telas são bonitas?**
Sim — usam o **design system do iTeam** (React). Você pode pedir pra mudar cores/estilo à vontade.

**E se eu quiser mudar algo depois?**
Peça pra IA. Ela faz **pull** do que existe (não recria do zero), edita e **redeploya** com o mesmo nome.

**Testes?**
Se você (ou a IA) definir um comando de teste, ele roda **antes** de publicar. Se falhar, **não publica** —
seu app no ar nunca quebra por um deploy ruim.

**Isso pesa no meu iTeam?**
Não. Roda numa **fazenda de servidores separada** (Service Farm), isolada do iTeam.

**Como removo algo?**
Pela aba Codes (excluir) ou peça pra IA parar o deploy. O container sai do ar e a rota some do gateway.
