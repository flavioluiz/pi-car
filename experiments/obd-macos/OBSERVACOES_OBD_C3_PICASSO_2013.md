# Observacoes OBD-II - Citroen C3 Picasso 2013 1.5 Flex

Documento de referencia para implementar um visualizador de dados OBD-II em tempo real na multimidia do carro.

As observacoes abaixo foram obtidas em um Raspberry Pi 4 conectado a um adaptador OBD-II USB baseado em ELM327/FTDI, ligado a um Citroen C3 Picasso 2013 1.5 Flex.

## Resumo operacional

- Veiculo: Citroen C3 Picasso 2013 1.5 Flex.
- Motor usado nos calculos: 1.449 cc, 4 cilindros, aspirado, flex.
- Computador: Raspberry Pi 4.
- Adaptador: ELM327 v2.1 via USB serial FTDI.
- Porta serial Linux: `/dev/ttyUSB0`.
- Alias estavel por ID: `/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_ABAQJ7HX-if00-port0`.
- Baudrate confirmado: `38400`.
- Protocolo OBD detectado: `ISO 15765-4 (CAN 11/500)`.
- Inicializacao ELM recomendada: `ATZ`, `ATE0`, `ATL0`, `ATS0`, `ATH0`, `ATSP0`.
- Status da comunicacao: adaptador e ECU respondendo.

## Identificacao do dispositivo USB

Saida relevante de `lsusb`:

```text
Bus 001 Device 003: ID 0403:6001 Future Technology Devices International, Ltd FT232 Serial (UART) IC
```

Saida relevante do kernel:

```text
ftdi_sio 1-1.2:1.0: FTDI USB Serial Device converter detected
usb 1-1.2: Detected FT232R
usb 1-1.2: FTDI USB Serial Device converter now attached to ttyUSB0
```

Metadados udev relevantes:

```text
DEVNAME=/dev/ttyUSB0
ID_BUS=usb
ID_VENDOR=FTDI
ID_MODEL=FT232R_USB_UART
ID_VENDOR_ID=0403
ID_MODEL_ID=6001
ID_SERIAL=FTDI_FT232R_USB_UART_ABAQJ7HX
DEVLINKS=/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_ABAQJ7HX-if00-port0 ...
```

Permissao observada:

```text
crw-rw-rw- 1 root dialout 188, 0 /dev/ttyUSB0
```

Na implementacao, prefira abrir o alias por ID quando existir:

```text
/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_ABAQJ7HX-if00-port0
```

Esse caminho e mais estavel que `/dev/ttyUSB0` quando houver mais de um adaptador serial conectado.

## Camadas de comunicacao

### Camada fisica/local

- USB no Raspberry Pi.
- Conversor serial FTDI FT232R.
- Device Linux: `/dev/ttyUSB0`.
- Configuracao serial:
  - baudrate: `38400`
  - data bits: `8`
  - parity: `none`
  - stop bits: `1`
  - controle de fluxo: nenhum
  - terminador de comando ELM: carriage return (`\r`)

### Camada adaptador

O adaptador responde como ELM327:

```text
ATZ -> ELM327 v2.1
```

Baudrates testados:

```text
38400  -> resposta valida: ELM327 v2.1
9600   -> bytes invalidos
115200 -> bytes invalidos
57600  -> bytes invalidos
```

### Camada veiculo

Com `ATSP0`, o ELM327 faz deteccao automatica de protocolo. A ECU respondeu:

```text
ATDP -> AUTO, ISO 15765-4 (CAN 11/500)
```

Isso significa:

- CAN 11-bit identifier.
- 500 kbit/s no barramento CAN.
- Requisicoes OBD-II funcionais/padrao via ELM327.

Na primeira tentativa, a ECU retornou:

```text
0100 -> BUS INIT: ...ERROR
```

Na tentativa seguinte, com a ignicao/ECU pronta, respondeu corretamente:

```text
0100 -> SEARCHING...
        4100BE3EF811
```

Conclusao: se aparecer `BUS INIT: ...ERROR`, nao assumir falha do adaptador. Pode ser ignicao desligada, ECU ainda inicializando, conector mal encaixado ou tentativa antes do barramento estar pronto.

## Sequencia recomendada de inicializacao

Para um servico persistente no Raspberry Pi:

```text
ATZ    reset do adaptador
ATE0   desliga echo
ATL0   desliga quebras de linha
ATS0   desliga espacos
ATH0   desliga headers CAN para leituras simples
ATSP0  protocolo automatico
0100   forca inicializacao e valida comunicacao com a ECU
ATDP   registra protocolo detectado
```

Para diagnostico mais detalhado, `ATH1` pode ser usado temporariamente para mostrar headers CAN, por exemplo `7E8`, mas para o visualizador em tempo real `ATH0` simplifica o parsing.

## PIDs OBD-II suportados pela ECU

Consulta de suporte:

```text
0100 -> 4100BE3EF811
0120 -> 412080000000
0140 -> NO DATA
0160 -> NO DATA
0180 -> NO DATA
01A0 -> NO DATA
0900 -> 490054000000
```

PIDs suportados no modo `01`:

```text
01, 03, 04, 05, 06, 07, 0B, 0C, 0D, 0E, 0F,
11, 12, 13, 14, 15, 1C, 20, 21
```

Servicos suportados no modo `09`:

```text
0902 VIN
0904 Calibration ID
0906 CVN
```

PIDs testados e sem suporte relevante:

```text
0110 MAF / Mass Air Flow: NO DATA
012F Fuel Level: NO DATA
015E Engine Fuel Rate: NO DATA
0140+ blocos acima de 0x40: NO DATA
0A permanent DTCs: NO DATA
```

## Varredura detalhada adicional

Varredura feita com o backend pausado temporariamente para evitar concorrencia
na porta serial. Configuracao usada:

```text
porta=/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_ABAQJ7HX-if00-port0
baudrate=38400
headers=off
spaces=off
linefeeds=off
protocol=ATSP0 automatico
```

Inicializacao observada:

```text
ATZ   -> ELM327 v2.1
ATE0  -> OK
ATL0  -> OK
ATS0  -> OK
ATH0  -> OK
ATSP0 -> OK
ATDP  -> AUTO
ATRV  -> 13.7V
```

Suporte modo `01`:

```text
0100 -> SEARCHING...
        4100BE3EF811
0120 -> 412080000000
0140 -> NO DATA
0160 -> NO DATA
0180 -> NO DATA
01A0 -> NO DATA
01C0 -> NO DATA
```

PIDs modo `01` confirmados como suportados nessa varredura:

```text
0101 Monitor status/MIL
0103 Fuel system status
0104 Calculated engine load
0105 Coolant temp
0106 STFT B1
0107 LTFT B1
010B MAP
010C RPM
010D Speed
010E Timing advance
010F Intake air temp
0111 Throttle position
0112 Secondary air status
0113 O2 sensors present
0114 O2 B1S1
0115 O2 B1S2
011C OBD standard
0120 PIDs 21-40
0121 Distance with MIL
```

Respostas brutas de PIDs suportados, amostra com motor ligado e carro parado:

```text
0101 Monitor status/MIL               -> 410100076100
0103 Fuel system status               -> 41030200
0104 Calculated engine load           -> 41048C
0105 Coolant temp                     -> 410591
0106 STFT B1                          -> 410682
0107 LTFT B1                          -> 410782
010B MAP                              -> 410B38
010C RPM                              -> 410C0C3C
010D Speed                            -> 410D00
010E Timing advance                   -> 410E85
010F Intake air temp                  -> 410F5D
0111 Throttle position                -> 411127
0112 Secondary air status             -> 411204
0113 O2 sensors present               -> 411303
0114 O2 B1S1                          -> 41141087
0115 O2 B1S2                          -> 411514FF
011C OBD standard                     -> 411C06
0121 Distance with MIL                -> 41210000
```

Conversoes dessa amostra:

```text
0104 carga calculada: 140 * 100 / 255 = 54.9%
0105 arrefecimento: 145 - 40 = 105 C
0106 STFT B1: (130 - 128) * 100 / 128 = 1.6%
0107 LTFT B1: (130 - 128) * 100 / 128 = 1.6%
010B MAP: 56 kPa
010C RPM: ((0x0C * 256) + 0x3C) / 4 = 783 rpm
010D velocidade: 0 km/h
010E avanco: (0x85 / 2) - 64 = 2.5 graus
010F IAT: 93 - 40 = 53 C
0111 acelerador: 39 * 100 / 255 = 15.3%
0114 O2 B1S1: tensao 0x10 / 200 = 0.080 V, trim 5.5%
0115 O2 B1S2: tensao 0x14 / 200 = 0.100 V, trim nao aplicavel/0xFF
0121 distancia com MIL ligada: 0 km
```

PIDs modo `01` candidatos uteis testados e indisponiveis:

```text
0110 MAF                              -> NO DATA
012F Fuel level                       -> NO DATA
0130 Warmups since DTC clear          -> NO DATA
0131 Distance since DTC clear         -> NO DATA
0133 Barometric pressure              -> NO DATA
0142 Control module voltage           -> NO DATA
0143 Absolute load                    -> NO DATA
0144 Commanded equivalence ratio      -> NO DATA
0145 Relative throttle                -> NO DATA
0146 Ambient air temp                 -> NO DATA
0151 Fuel type                        -> NO DATA
0152 Ethanol fuel percent             -> NO DATA
015E Engine fuel rate                 -> NO DATA
```

Conclusao sobre combustivel/composicao:

```text
0151 Fuel type               indisponivel
0152 Ethanol fuel percentage indisponivel
015E Engine fuel rate        indisponivel
```

Portanto, a proporcao gasolina/etanol nao esta disponivel por OBD-II padrao
nessa ECU. Para isso, usar entrada manual/estimativa por abastecimento ou
investigar PIDs proprietarios PSA/Citroen em experimento separado.

DTCs:

```text
03 -> 4300
07 -> 4700
0A -> NO DATA
```

Interpretacao:

```text
03 DTCs ativos: nenhum
07 DTCs pendentes: nenhum
0A DTCs permanentes: servico indisponivel
```

Modo `09`:

```text
0900 Mode 09 supported info -> 490054000000
0902 VIN                    -> multi-frame disponivel
0904 Calibration ID         -> multi-frame disponivel
0906 CVN                    -> 4906010C4C0000
0908 IPT                    -> NO DATA
090A ECU name               -> NO DATA
```

Resposta bruta do VIN:

```text
0902 -> 014
        0:490201393335
        1:53445946595944
        2:42353336343131
```

VIN decodificado:

```text
935SDMFYYDB536411
```

Resposta bruta do Calibration ID:

```text
0904 -> 013
        0:490401393636
        1:37333431353939
        2:00000000000031
```

Calibration ID decodificado parcialmente:

```text
96673415991
```

CVN:

```text
0906 -> 4906010C4C0000
CVN  -> 0C4C0000
```

### Mode 06 - monitores onboard

O modo `06` respondeu e pode ser usado futuramente em uma tela tecnica de
monitores onboard. As respostas sao brutas e precisam de decoder especifico por
TID/CID para ficarem amigaveis.

Suporte/bitmaps observados:

```text
0600 -> 4600C0000001
0620 -> 462080000001
0640 -> 4640C0000001
0660 -> 466000000001
0680 -> 468080000000
```

TIDs consultados a partir desses bitmaps:

```text
0601 -> SEARCHING...
        040
        0:4601010B01C6
        1:0000FFFF01020B
        2:01C60000FFFF01
        3:070B00270000FF
        4:FF01080B037E00
        5:00FFFF01510C00
        6:40000001D60153
        7:0C000000000000
        8:01540C00000000
        9:00000000000000

0602 -> 040
        0:4602010B01C6
        1:0000FFFF02020B
        2:01C60000FFFF02
        3:070B0000000000
        4:0002080B037900
        5:00FFFF02520C00
        6:0D000001D60253
        7:0C000000000000
        8:02540C00000000
        9:00000000000000

0621 -> 00A
        0:462181036FFC
        1:00009F4002020B

0641 -> 00A
        0:4641A10B0155
        1:015F030D02020B

0642 -> 00A
        0:4642A10B004E
        1:015F022C02020B

0681 -> 013
        0:4681AAB0019D
        1:E0201FE081BAAA
        2:FE27FE00020002
```

Recomendacao: manter Mode 06 fora do loop principal de tempo real. Se usado,
consultar sob demanda em tela tecnica, porque as respostas podem ser
multi-frame e mais longas que os PIDs dinamicos.

## Dados diretos disponiveis

Tabela de dados que podem ser retirados diretamente da ECU via OBD-II padrao.

| Dado | PID/servico | Exemplo bruto | Conversao | Exemplo observado |
|---|---:|---|---|---:|
| Status MIL e monitores | `0101` | `410100076100` | bitfields OBD | MIL apagada |
| Status do sistema de combustivel | `0103` | `41030200` | bitfields OBD | closed-loop em um banco |
| Carga calculada do motor | `0104` | `41046E` | `A * 100 / 255` | 43.1% |
| Temperatura do arrefecimento | `0105` | `41058F` | `A - 40` | 103 C |
| Short fuel trim banco 1 | `0106` | `410687` | `(A - 128) * 100 / 128` | 5.5% |
| Long fuel trim banco 1 | `0107` | `410783` | `(A - 128) * 100 / 128` | 2.3% |
| Pressao MAP | `010B` | `410B2B` | `A` | 43 kPa |
| RPM | `010C` | `410C0B2C` | `((A * 256) + B) / 4` | 715 rpm |
| Velocidade | `010D` | `410D00` | `A` | 0 km/h |
| Avanco de ignicao | `010E` | `410E79` | `(A / 2) - 64` | -3.5 graus |
| Temperatura do ar de admissao | `010F` | `410F67` | `A - 40` | 63 C |
| Posicao do acelerador | `0111` | `411124` | `A * 100 / 255` | 14.1% |
| Ar secundario comandado | `0112` | `411204` | enum OBD | disponivel |
| Sensores O2 presentes | `0113` | `411303` | bitmask | B1S1 e B1S2 |
| O2 sensor 1 | `0114` | `41148E83` | tensao `A / 200`, trim `(B - 128) * 100 / 128` | 0.71 V |
| O2 sensor 2 | `0115` | `41151FFF` | tensao `A / 200`, trim se valido | 0.155 V |
| Padrao OBD | `011C` | `411C06` | enum OBD | EOBD/OBD compativel |
| PIDs 0x21-0x40 suportados | `0120` | `412080000000` | bitmask | apenas `0121` |
| Distancia com MIL ligada | `0121` | `41210000` | `(A * 256) + B` | 0 km |
| VIN | `0902` | multi-frame | ASCII | `935SDMFYYDB536411` |
| Calibration ID | `0904` | multi-frame | ASCII | disponivel |
| CVN | `0906` | `4906010C4C0000` | hexadecimal/CVN | disponivel |
| Tensao no adaptador | `ATRV` | `13.9V` | texto ELM | 13.9 V |
| DTCs ativos | `03` | `4300` | lista DTC | nenhum |
| DTCs pendentes | `07` | `4700` | lista DTC | nenhum |

Valores observados sao amostras de um momento especifico, com o carro parado. O visualizador deve tratar esses valores como dinamicos.

## Dados inferidos possiveis

### Consumo instantaneo estimado

A ECU nao fornece consumo direto por OBD-II padrao neste carro. Portanto, o consumo deve ser inferido.

PIDs diretos ausentes:

```text
0110 MAF: NO DATA
015E Engine Fuel Rate: NO DATA
012F Fuel Level: NO DATA
```

Como o MAF nao esta disponivel, usar estimativa speed-density com:

- `010B` MAP em kPa.
- `010C` RPM.
- `010F` temperatura do ar de admissao.
- cilindrada: `1.449 L`.
- eficiencia volumetrica estimada.
- correcao por fuel trims `0106` e `0107`.
- relacao ar/combustivel conforme combustivel.

Formula base:

```text
intake_events_per_s = RPM / 2 / 60
volume_m3_s = displacement_l / 1000 * intake_events_per_s * VE
air_g_s = (MAP_pa * volume_m3_s / (R * temp_k)) * air_molar_mass_g_mol
air_g_s_corrigido = air_g_s * (1 + (STFT + LTFT) / 100)
fuel_g_s = air_g_s_corrigido / AFR
fuel_l_h = fuel_g_s * 3600 / fuel_density_g_l
```

Constantes sugeridas:

```text
displacement_l = 1.449
R = 8.314
air_molar_mass_g_mol = 28.97
VE inicial = 0.78
AFR gasolina brasileira/E27 ~= 13.2
densidade gasolina ~= 745 g/L
AFR etanol ~= 9.0
densidade etanol ~= 789 g/L
```

Exemplo observado em marcha lenta:

```text
MAP=39 kPa
RPM=721
speed=0 km/h
IAT=67 C
STFT=2.3%
LTFT=2.3%
VE=0.78
```

Estimativa resultante:

```text
gasolina/E27: 1.04 L/h parado
etanol/E100:  1.44 L/h parado
```

Quando `010D` velocidade for maior que zero:

```text
km_l = speed_kmh / fuel_l_h
l_100km = 100 / km_l
```

Quando o carro estiver parado, exibir apenas `L/h`; `km/L` nao faz sentido com velocidade zero.

### Autonomia estimada

Como `012F Fuel Level` nao esta disponivel, autonomia precisa de uma fonte externa:

- entrada manual do volume no tanque;
- integracao por consumo acumulado desde abastecimento;
- leitura proprietaria PSA/Citroen, se descoberta;
- dado da multimidia/CAN fora do OBD-II padrao, se disponivel.

Sem nivel do tanque, o sistema pode exibir consumo instantaneo e medio, mas autonomia sera estimada e dependente de calibracao.

### Consumo medio acumulado

Pode ser calculado localmente pelo visualizador:

```text
litros_consumidos += fuel_l_h * delta_t_h
distancia_km += speed_kmh * delta_t_h
km_l_medio = distancia_km / litros_consumidos
```

Recomendacoes:

- ignorar amostras com velocidade absurda ou RPM invalido;
- persistir acumuladores em disco para sobreviver a reinicializacao;
- permitir reset manual pelo usuario;
- separar media da viagem atual e media historica.

### Estado do motor e alertas

Inferencias uteis para interface:

- motor ligado: RPM maior que zero;
- carro parado: velocidade igual a zero;
- marcha lenta: RPM entre aproximadamente 600 e 1000 e velocidade zero;
- possivel aquecimento: arrefecimento acima de limite configuravel;
- aquecimento concluido: arrefecimento acima de aproximadamente 70 C;
- carga elevada: `0104` alto;
- mistura adaptando: STFT/LTFT longe de zero;
- check engine: MIL em `0101`;
- bateria/alternador: `ATRV` com motor ligado deve ficar tipicamente acima de 13 V.

## Observacoes sobre dados que apps podem mostrar a mais

O adaptador Bluetooth usado anteriormente provavelmente nao oferecia mais dados por ser Bluetooth. As diferencas mais provaveis:

1. O app calculava dados derivados, como consumo instantaneo e medio.
2. O app usava PIDs proprietarios PSA/Citroen, fora do OBD-II padrao.
3. O app consultava outros modulos, nao apenas a ECU por OBD-II generico.
4. O app mostrava campos derivados com nomes amigaveis.

Para reproduzir esses dados, o caminho recomendado e:

1. Implementar bem o conjunto OBD-II padrao listado neste documento.
2. Adicionar calculos inferidos no backend.
3. Depois investigar PIDs proprietarios PSA/Citroen com seguranca, de forma isolada.

## Requisitos para o visualizador em tempo real

### Backend OBD

O backend deve manter uma conexao serial persistente com o ELM327 e publicar snapshots normalizados para a multimidia.

Configuracao minima:

```text
port=/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_ABAQJ7HX-if00-port0
fallback_port=/dev/ttyUSB0
baudrate=38400
protocol=auto
detected_protocol=ISO 15765-4 (CAN 11/500)
command_terminator=\r
```

Loop recomendado:

1. abrir porta serial;
2. inicializar ELM com comandos AT;
3. validar ECU com `0100`;
4. registrar `ATDP`;
5. iniciar polling de PIDs;
6. decodificar respostas;
7. calcular dados inferidos;
8. publicar snapshot;
9. em erro, tentar recuperar com backoff.

### Frequencia de polling

Nem todos os dados precisam ser lidos na mesma frequencia.

Leituras rapidas, 2 a 5 Hz:

```text
010C RPM
010D velocidade
010B MAP
0111 acelerador
0104 carga
```

Leituras medias, 1 Hz:

```text
0105 temperatura do motor
010F temperatura do ar
0106 STFT
0107 LTFT
010E avanco
ATRV tensao
```

Leituras lentas, sob demanda ou a cada 30-60 s:

```text
0101 status MIL
03 DTCs ativos
07 DTCs pendentes
0902 VIN
0904 Calibration ID
0906 CVN
```

Na implementacao atual do `pi-car`, a cadencia foi ajustada de forma mais
conservadora para evitar travamentos/atrasos em ELM327 barato:

```text
OBD_POLL_INTERVAL = 0.8 s
```

Leituras rapidas em cada ciclo:

```text
010C RPM
010D velocidade
010B MAP
0104 carga do motor
0111 acelerador
```

Leituras medias a cada aproximadamente 1 s:

```text
0105 temperatura do motor
010F temperatura do ar de admissao
0106 STFT banco 1
0107 LTFT banco 1
010E avanco de ignicao
ATRV tensao do adaptador
```

Leituras lentas a cada aproximadamente 30 s:

```text
0101 status MIL
03 DTCs ativos
07 DTCs pendentes
```

Observacao importante: quando um PID individual retorna `NO DATA`, timeout,
resposta parcial ou resposta nao parseavel, o backend preserva o ultimo valor
valido daquele campo em vez de substituir por `null`. Isso evita que a tela
mostre "waiting for vehicle data" depois de falhas transientes de polling. Um
campo so permanece `null` quando ainda nao houve nenhuma leitura valida desde a
inicializacao/reconexao.

### Campos recomendados no snapshot

Exemplo de estrutura para publicar via WebSocket, HTTP polling local ou IPC:

```json
{
  "connection": {
    "connected": true,
    "port": "/dev/ttyUSB0",
    "stable_port": "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_ABAQJ7HX-if00-port0",
    "baudrate": 38400,
    "adapter": "ELM327 v2.1",
    "protocol": "ISO 15765-4 (CAN 11/500)"
  },
  "direct": {
    "rpm": 721,
    "speed_kmh": 0,
    "coolant_temp_c": 99,
    "intake_temp_c": 67,
    "map_kpa": 39,
    "engine_load_pct": 37.6,
    "throttle_pct": 13.7,
    "timing_advance_deg": -4.0,
    "short_fuel_trim_b1_pct": 2.3,
    "long_fuel_trim_b1_pct": 2.3,
    "adapter_voltage_v": 13.9,
    "mil_on": false,
    "active_dtcs": [],
    "pending_dtcs": []
  },
  "inferred": {
    "engine_on": true,
    "fuel_rate_l_h_gasoline_e27": 1.04,
    "fuel_rate_l_h_ethanol": 1.44,
    "instant_km_l": null,
    "instant_l_100km": null,
    "trip_consumed_l": 0.0,
    "trip_distance_km": 0.0,
    "trip_average_km_l": null
  },
  "metadata": {
    "vehicle": "Citroen C3 Picasso 2013 1.5 Flex",
    "vin": "935SDMFYYDB536411",
    "sample_time": "2026-04-30T17:00:00-03:00"
  }
}
```

### Interface na multimidia

Dados bons para tela principal:

- RPM;
- velocidade;
- temperatura do motor;
- consumo instantaneo;
- consumo medio da viagem;
- tensao/bateria;
- status check engine;
- alerta de temperatura;
- combustivel inferido/configurado: gasolina ou etanol.

Dados bons para tela tecnica:

- MAP;
- IAT;
- carga do motor;
- acelerador;
- avanco;
- STFT/LTFT;
- O2 B1S1/B1S2;
- protocolo, porta, baudrate;
- DTCs.

Configuracoes necessarias:

- combustivel atual: gasolina/E27, etanol ou automatico/manual;
- VE/calibracao do consumo;
- reset de viagem;
- porta serial preferida;
- intervalo de polling;
- limites de alerta.

### Implementacao atual no pi-car

Arquivos principais:

```text
config.py
backend/services/obd_service.py
backend/routes/vehicle.py
frontend/templates/index.html
frontend/static/js/app.js
frontend/static/css/style.css
```

Backend:

- abre primeiro `/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_ABAQJ7HX-if00-port0`;
- usa fallback `/dev/ttyUSB0`;
- configura serial em `38400 8N1`, sem controle de fluxo;
- inicializa o ELM327 com `ATZ`, `ATE0`, `ATL0`, `ATS0`, `ATH0`, `ATSP0`;
- valida ECU com `0100`;
- registra protocolo com `ATDP`;
- publica snapshot normalizado com `connection`, `direct`, `inferred`,
  `metadata`, `metrics` e `error`;
- calcula consumo por speed-density para gasolina/E27 e etanol;
- seleciona o consumo exibido conforme combustivel configurado;
- acumula distancia e litros consumidos da viagem;
- preserva o ultimo valor valido por PID em falhas transientes;
- tenta reconectar em caso de desconexao ou erro de porta.

Endpoints HTTP:

```text
GET  /api/vehicle/status
GET  /api/vehicle/supported
POST /api/vehicle/settings
POST /api/vehicle/trip/reset
GET  /api/status
```

`POST /api/vehicle/settings` aceita atualmente:

```json
{
  "fuel": "gasoline_e27"
}
```

Valores aceitos para `fuel`:

```text
gasoline_e27
ethanol
```

`POST /api/vehicle/trip/reset` zera:

```text
trip_consumed_l
trip_distance_km
trip_average_km_l
```

Frontend:

- tela principal OBD mostra velocidade, RPM, temperatura do motor e consumo;
- parado, exibe consumo em `L/h`;
- em movimento, quando houver velocidade e consumo, exibe consumo em `km/L`;
- mostra distancia da viagem, litros consumidos, media da viagem e tensao;
- mostra alertas de check engine, temperatura, tensao baixa e DTCs;
- mostra painel tecnico com MAP, IAT, carga, acelerador, avanco, STFT/LTFT e
  estimativas de consumo;
- permite alternar combustivel entre gasolina/E27 e etanol;
- permite resetar a viagem pela interface.

Durante testes em tempo real tambem foi corrigido o loop do GPS para dormir
quando `gpsd` nao entrega dado novo. Sem isso, o processo Flask podia ficar com
CPU alta e prejudicar a responsividade da interface enquanto o OBD estava sendo
lido.

## Tratamento de erros

Casos observados ou esperados:

```text
BUS INIT: ...ERROR
NO DATA
?
resposta parcial sem prompt >
desconexao USB
porta ocupada
ECU dormindo
```

Recomendacoes:

- tratar `BUS INIT: ...ERROR` como falha recuperavel;
- nao derrubar a aplicacao por `NO DATA`;
- marcar cada PID com timestamp da ultima leitura valida;
- se a porta sumir, tentar reabrir a cada alguns segundos;
- se o ELM responder mas a ECU nao, mostrar "adaptador conectado, ECU sem dados";
- ao reconectar, repetir toda a sequencia AT;
- evitar polling agressivo demais, pois ELM327 barato pode travar ou atrasar.

Comportamento implementado apos testes:

- `NO DATA` em um PID isolado nao apaga o ultimo valor valido;
- timeouts ou respostas incompletas em um PID isolado nao derrubam a conexao;
- o snapshot continua `connected=true` quando o adaptador e a ECU seguem
  respondendo, mesmo que alguns PIDs falhem momentaneamente;
- se todos os PIDs dinamicos ainda estiverem sem leitura valida, a interface
  mostra estado de espera para dados tecnicos, mas a conexao continua indicada;
- a tela deve ser testada com ignicao/ECU acordada, pois com ECU dormindo o
  adaptador pode responder `ATRV` e comandos AT sem fornecer PIDs do motor.

## Referencias externas usadas para parametros do veiculo

- Ficha tecnica Heycar: https://www.heycar.com.br/ficha-tecnica/ficha-tecnica-completa-do-citroen-c3-picasso-glx-1-5-2013
- Automobile Catalog, C3 Picasso 2013 Brasil: https://www.automobile-catalog.com/make/citroen_brasil/c3_picasso_br_1gen/c3_picasso_br_1/2013.html

Essas referencias foram usadas apenas para confirmar dados estaticos do veiculo, especialmente cilindrada aproximada de 1.449 cc e motorizacao flex. As leituras OBD foram obtidas diretamente no Raspberry Pi conectado ao carro.
