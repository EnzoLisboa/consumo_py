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

### 1. Prepare os arquivos

Coloque os CSVs de medições em qualquer pasta do seu computador (a pasta `dados/`
do repositório é apenas uma sugestão). Cada linha deve conter um timestamp e o
valor de potência medido — ou, alternativamente, tensão e corrente.

### 2. Execute o comando básico

Abra um terminal na pasta onde está `consumo.py` e rode:

```bash
python consumo.py CAMINHO/DO/ARQUIVO.csv \
    --time-column Timestamp \
    --power-column Power_W
```

Substitua `CAMINHO/DO/ARQUIVO.csv` pelo arquivo (ou pasta) que você quer
analisar e ajuste os nomes das colunas de acordo com o seu CSV. Para processar
toda uma pasta de arquivos CSV, passe o diretório em vez de um arquivo único:

```bash
python consumo.py dados/
```

### 3. Converta porcentagens para watts (ex.: sistema de 60 W)

Se o seu equipamento registra a potência em porcentagem, informe o fator de
escala com `--power-scale`. Para um sistema cujo valor de 100% equivale a 60 W
(como no seu caso), use `0.6`:

```bash
python consumo.py dados/medicoes.csv \
    --time-column Timestamp_PC \
    --power-column Lamp_Power_Percent \
    --power-scale 0.6
```

O argumento multiplica cada leitura pela constante informada (por exemplo,
50% × 0.6 = 30 W).

### 4. Leia o relatório

O programa imprime um resumo com o intervalo das medições, o número de amostras
válidas e o consumo estimado em Wh/kWh. Se mais de um arquivo for processado, um
resumo consolidado com todos os arquivos também é exibido.

### Colunas aceitas

- `--time-column`: coluna com o instante de cada medição. Por padrão espera-se `timestamp` em formato ISO 8601.
- `--power-column`: coluna com valores de potência. Informe uma string vazia (`""`) para usá-la em conjunto com tensão e corrente.
- `--voltage-column` e `--current-column`: nomes das colunas com tensão (V) e corrente (A), respectivamente. São usadas apenas quando não há coluna de potência.
- `--power-scale`: fator multiplicativo aplicado à coluna de potência (ou ao
  produto tensão × corrente). Útil quando a medição é fornecida em porcentagem
  ou em outra escala.
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

