# OBD-II macOS Testing Scripts

Scripts de teste para desenvolvimento e validação do suporte OBD-II no projeto pi-car, especialmente úteis para testar com ELM327 via Bluetooth no macOS antes de integrar ao Raspberry Pi.

## Objetivo

Estes scripts permitem:
- **Descobrir** todos os comandos OBD-II suportados pelo seu veículo específico
- **Monitorar** dados em tempo real durante o desenvolvimento
- **Validar** a comunicação com o adaptador ELM327 antes da integração

## Pré-requisitos

### 1. Parear o ELM327 via Bluetooth no macOS

1. Abra **Preferências do Sistema** > **Bluetooth**
2. Pareie o adaptador ELM327 (geralmente aparece como "OBDII" ou "ELM327")
3. Aguarde o pareamento completar

### 2. Identificar a porta serial

```bash
ls /dev/tty.* | grep -i obd
```

Ou procure por algo como:
- `/dev/tty.OBDII-SPPDev`
- `/dev/tty.ELM327`
- `/dev/tty.OBD*`

### 3. Criar ambiente Python

```bash
cd ~/pi-car/experiments/obd-macos
python3 -m venv venv
source venv/bin/activate
pip install obd
```

## Scripts Disponíveis

### `obd_discovery.py`

Descobre **todos os comandos OBD-II suportados** pelo seu veículo.

**Uso:**

1. Edite o script e ajuste a variável `PORT` com a porta correta:
   ```python
   PORT = "/dev/tty.OBDII-SPPDev"  # Ajuste conforme necessário
   ```

2. Execute:
   ```bash
   python3 obd_discovery.py
   ```

**Saída esperada:**

```
Conectando ao OBD...
Conectado! Protocolo: ISO 15765-4 (CAN 11/500)
Porta: /dev/tty.OBDII-SPPDev

============================================================
COMANDOS SUPORTADOS PELO VEÍCULO:
============================================================

✓ RPM
  Descrição: Engine RPM
  Valor: 850.0 revolutions_per_minute

✓ SPEED
  Descrição: Vehicle Speed
  Valor: 0.0 kilometers_per_hour

✓ COOLANT_TEMP
  Descrição: Engine Coolant Temperature
  Valor: 87.0 degree_celsius

...

============================================================
TOTAL: 47 comandos disponíveis
============================================================
```

### `obd_monitor.py`

Monitora dados OBD-II em **tempo real** com atualização contínua.

**Uso:**

1. Edite o script e ajuste a variável `PORT`:
   ```python
   PORT = "/dev/tty.OBDII-SPPDev"
   ```

2. Execute (com o carro ligado):
   ```bash
   python3 obd_monitor.py
   ```

3. Pressione `Ctrl+C` para sair

**Saída esperada:**

```
========================================
  PI-CAR OBD MONITOR
========================================
RPM                  850.0 revolutions_per_minute
SPEED                0.0 kilometers_per_hour
COOLANT_TEMP         87.0 degree_celsius
THROTTLE_POS         15.3 percent
ENGINE_LOAD          23.5 percent
FUEL_LEVEL           75.0 percent
INTAKE_TEMP          35.0 degree_celsius
MAF                  2.5 grams_per_second
```

## Customização

### Ajustar comandos monitorados

No `obd_monitor.py`, edite a lista `COMMANDS`:

```python
COMMANDS = [
    obd.commands.RPM,
    obd.commands.SPEED,
    obd.commands.COOLANT_TEMP,
    # Adicione outros comandos aqui
]
```

### Ajustar velocidade de atualização

No `obd_monitor.py`, altere o valor em `time.sleep()`:

```python
time.sleep(0.5)  # Altere para 1.0 para atualização mais lenta
```

## Solução de Problemas

### Erro: "Não foi possível conectar ao OBD"

**Causas comuns:**
1. Porta incorreta - verifique com `ls /dev/tty.*`
2. ELM327 não pareado - verifique em Preferências do Sistema > Bluetooth
3. Veículo não ligado ou adaptador mal conectado ao OBD
4. Biblioteca obd não instalada - execute `pip install obd`

### Comandos retornam "Sem valor"

Alguns veículos não suportam todos os comandos. Use o `obd_discovery.py` para identificar quais comandos funcionam no seu veículo específico.

### Timeout ou respostas lentas

Alguns adaptadores ELM327 mais baratos podem ter latência maior. Ajuste:
- Aumente `time.sleep()` no monitor
- Use um adaptador ELM327 de melhor qualidade

## Próximos Passos

Após testar com sucesso:

1. **Documente** os comandos suportados pelo seu veículo
2. **Anote** a velocidade de atualização ideal (0.5s? 1s?)
3. **Registre** problemas encontrados (timeouts, comandos que falham)
4. **Integre** ao `backend/services/obd_service.py` no projeto principal

## Estrutura para Integração

Com base nos testes, você pode atualizar o `backend/services/obd_service.py`:

```python
# Adicionar novos comandos descobertos
# Ajustar tratamento de erros
# Melhorar estrutura de dados retornada
# Otimizar velocidade de atualização
```

## Referências

- [python-obd Documentation](https://python-obd.readthedocs.io/)
- [ELM327 Protocol](https://www.elmelectronics.com/wp-content/uploads/2016/07/ELM327DS.pdf)
- [OBD-II PIDs](https://en.wikipedia.org/wiki/OBD-II_PIDs)
