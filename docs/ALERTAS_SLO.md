# SLO e alertas iniciais

## Objetivos iniciais

| Sinal | Objetivo | Janela | Método |
|---|---:|---|---|
| Disponibilidade da API | 99,5% | 30 dias | `health/ready` |
| Sucesso de chat | 99% | 30 dias | status HTTP do endpoint público |
| Latência de chat | 95% abaixo de 3 s | 30 dias | middleware de requisição |
| Taxa de upload válido | 95% | 30 dias | status HTTP e erros de documento |

## Alertas mínimos

- Disponibilidade abaixo de 99,5%.
- Mais de 5% de respostas `5xx` em 10 minutos.
- Tempo de resposta de chat acima de 3 segundos no percentil 95.
- `429` acima de 10% em 10 minutos.
- Banco indisponível no readiness probe.
- Falha contínua do provedor de IA.
- Uso de disco ou memória acima de 85%.

## Implementação

O backend fornece:

- `/health/live` para o processo.
- `/health/ready` para dependência de banco.
- `/api/metrics` para contagens autenticadas, uptime e respostas HTTP.

Logs estruturados incluem método, caminho, status e duração. Em produção, exporte esses dados para Prometheus, OpenTelemetry ou fornecedor equivalente e configure alertas no sistema externo.
