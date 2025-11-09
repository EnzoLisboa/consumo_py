# Consumo de Energia a partir de CSV

Ferramenta de linha de comando em Python para estimar o consumo de energia elétrica com base em medições registradas em um arquivo CSV.

## Instalação

O projeto não possui dependências externas além da biblioteca padrão do Python. Basta garantir que o Python 3.9 (ou superior) esteja instalado no sistema.

Clone o repositório ou copie o arquivo `consumo.py` para o seu ambiente de trabalho.

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows PowerShell
```

## Uso

O script é executado a partir da linha de comando. Passe o caminho do arquivo CSV e informe como as colunas estão organizadas.

```bash
python consumo.py mediacoes.csv \
    --delimiter ';' \
    --time-column timestamp \
    --power-column potencia
```

### Colunas aceitas

- `--time-column`: coluna com o instante de cada medição. Por padrão espera-se `timestamp` em formato ISO 8601.
- `--power-column`: coluna com valores de potência (em watts). Informe uma string vazia (`""`) para usá-la em conjunto com tensão e corrente.
- `--voltage-column` e `--current-column`: nomes das colunas com tensão (V) e corrente (A), respectivamente. São usadas apenas quando não há coluna de potência.
- `--time-format`: permite especificar explicitamente o formato do horário usando diretivas `strftime` (ex.: `%d/%m/%Y %H:%M`).

### Saída

Após processar o CSV, o programa imprime um resumo com o período das medições, quantidade de amostras e o consumo total estimado em watt-hora (Wh) e quilowatt-hora (kWh).

Exemplo de saída:

```
Resumo das medições:
  Início: 2024-01-01 00:00:00
  Fim: 2024-01-01 23:59:00
  Duração: 24.00 h
  Amostras: 96

Consumo estimado:
  12450.00 Wh
  12.4500 kWh
```

## Funcionamento interno

1. **Leitura do CSV:** o arquivo é percorrido usando `csv.DictReader`. O script valida se as colunas informadas existem e converte os valores numéricos para `float`, aceitando vírgulas como separador decimal.
2. **Conversão de timestamps:** os horários são convertidos para `datetime`. Se `--time-format` não for informado, o valor é interpretado automaticamente no formato ISO 8601.
3. **Cálculo da potência:** se a coluna de potência for fornecida, ela é utilizada diretamente. Caso contrário, a potência é calculada multiplicando tensão por corrente.
4. **Integração trapezoidal:** as amostras são ordenadas cronologicamente e é aplicado o método dos trapézios para integrar a potência em relação ao tempo, resultando em watt-hora.
5. **Relatório:** ao final, o programa informa o consumo total em Wh e kWh, além de um resumo das medições analisadas.

## Testes

Não há suíte de testes automatizados. Para validar o funcionamento, recomenda-se preparar um CSV pequeno com timestamps e potência conhecida e comparar o resultado calculado com o esperado.

