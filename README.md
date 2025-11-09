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
do repositório é apenas uma sugestão). Cada linha deve conter:

- `Timestamp_PC` com o instante da medição (em ISO 8601 ou no formato
  configurado via `--time-format`).
- `Lamp_Power_Percent` com o percentual de potência registrado pelo sistema.

### 2. Execute o comando básico

Abra um terminal na pasta onde está `consumo.py` e rode:

```bash
python consumo.py CAMINHO/DO/ARQUIVO.csv
```

Substitua `CAMINHO/DO/ARQUIVO.csv` pelo arquivo (ou pasta) que você quer
analisar. Para processar toda uma pasta de arquivos CSV, passe o diretório em
vez de um arquivo único:

```bash
python consumo.py dados/
```

Por padrão o script espera as colunas `Timestamp_PC` e `Lamp_Power_Percent`.
Caso os nomes sejam diferentes, ajuste-os com `--time-column` e
`--percent-column`.

### 3. Potência total do sistema

O script converte automaticamente o percentual em watts considerando que 100%
corresponde à potência máxima do sistema definida no código (por padrão, 60 W).
Se precisar alterar esse valor, edite a constante `SYSTEM_TOTAL_POWER_WATTS` em
`consumo.py`.

### 4. Leia o relatório

O programa imprime um resumo com o intervalo das medições, o número de amostras
válidas e o consumo estimado em kW/h. Se mais de um arquivo for processado, um
resumo consolidado com todos os arquivos também é exibido.

### Colunas aceitas

- `--time-column`: coluna com o instante de cada medição. Por padrão espera-se `Timestamp_PC` em formato ISO 8601.
- `--percent-column`: coluna com valores percentuais de potência (0 a 100).
- `--time-format`: permite especificar explicitamente o formato do horário usando diretivas `strftime` (ex.: `%d/%m/%Y %H:%M`).

### Saída

Após processar o CSV, o programa imprime um resumo com o período das medições, quantidade de amostras e o consumo total estimado em quilowatt por hora (kW/h).

Exemplo de saída:

```
Resumo das medições:
  Início: 2024-01-01 00:00:00
  Fim: 2024-01-01 23:59:00
  Duração: 24.00 h
  Amostras: 96

Consumo estimado:
  12.4500 kW/h
```

## Funcionamento interno

1. **Leitura do CSV:** o arquivo é percorrido usando `csv.DictReader`. O script valida se as colunas informadas existem e converte os valores numéricos para `float`, aceitando vírgulas como separador decimal.
2. **Conversão de timestamps:** os horários são convertidos para `datetime`. Se `--time-format` não for informado, o valor é interpretado automaticamente no formato ISO 8601.
3. **Cálculo da potência:** a coluna percentual é convertida em watts usando a
   constante `SYSTEM_TOTAL_POWER_WATTS` (por padrão, 60 W).
4. **Integração trapezoidal:** as amostras são ordenadas cronologicamente e é aplicado o método dos trapézios para integrar a potência em relação ao tempo, resultando em watt-hora.
5. **Relatório:** ao final, o programa informa o consumo total em kW/h, além de um resumo das medições analisadas.

## Testes

Não há suíte de testes automatizados. Para validar o funcionamento, recomenda-se preparar um CSV pequeno com timestamps e potência conhecida e comparar o resultado calculado com o esperado.

