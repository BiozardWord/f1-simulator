# 🏎️ F1 Simulator

[![CI](https://github.com/BiozardWord/f1-simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/BiozardWord/f1-simulator/actions/workflows/ci.yml)

Simulador de corrida de F1 em Python com:
- Tipagem 100% strict (basedpyright)
- 11 testes automatizados (pytest)
- IA de oponentes com 5 personalidades diferentes
- Campeonato multi-rodada com classificação
- Save/load em JSON
- Efeitos sonoros (com fallback silencioso)
- CI/CD rodando a cada push

## Como rodar

    pip install -r requirements.txt
    python f1_simulator.py

## Verificacoes

    python -m basedpyright
    python -m pytest tests/ -v

Ou, no Windows:

    .\check.ps1

## Estrutura

    fomula 1/
    ├── f1_simulator.py         # Jogo principal
    ├── pyrightconfig.json      # Configuracao strict
    ├── requirements.txt        # Dependencias
    ├── check.ps1               # Script de verificacao
    ├── .github/workflows/      # CI/CD
    ├── data/                   # JSONs (pilotos, circuitos, save)
    ├── sounds/                 # Audios (opcional)
    ├── images/                 # Imagens (opcional)
    └── tests/                  # Testes unitarios

## Licenca

Uso pessoal e educacional.
