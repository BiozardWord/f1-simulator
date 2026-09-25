# pyright: strict
"""F1 Simulator – The Real Experience.

Versão compatível com pyright/Pylance no modo Strict.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from enum import Enum
from typing import Any, Callable, Protocol, cast

import pygame


# ============================================================
#  TIPOS AUXILIARES
# ============================================================

class Racer(Protocol):
    """Qualquer coisa com posição e estado de desistência."""

    posicao: int
    desistiu: bool


class Personality(str, Enum):
    AGRESSIVO = "agressivo"
    CONSERVADOR = "conservador"
    EQUILIBRADO = "equilibrado"
    TALENTOSO = "talentoso"
    IMPREVISIVEL = "imprevisivel"


# ============================================================
#  GERENCIADOR DE SOM
# ============================================================

class SoundManager:
    ARQUIVOS: dict[str, str] = {
        "motor":         os.path.join("sounds", "engine.wav"),
        "torcida":       os.path.join("sounds", "crowd.wav"),
        "batida":        os.path.join("sounds", "crash.wav"),
        "pitstop":       os.path.join("sounds", "pitstop.wav"),
        "ultrapassagem": os.path.join("sounds", "overtake.wav"),
    }

    def __init__(self) -> None:
        self.sons: dict[str, pygame.mixer.Sound] = {}
        self._ativos: set[str] = set()
        self._carregar()

    def _carregar(self) -> None:
        carregados: list[str] = []
        ausentes: list[str] = []
        for chave, caminho in self.ARQUIVOS.items():
            if os.path.exists(caminho):
                try:
                    self.sons[chave] = pygame.mixer.Sound(caminho)
                    carregados.append(chave)
                except pygame.error as e:
                    ausentes.append(f"{chave}({e})")
            else:
                ausentes.append(chave)

        if carregados:
            print(f"🔊 Sons carregados: {', '.join(carregados)}")
        if ausentes:
            print(f"🔇 Sons ausentes (modo silencioso): {', '.join(ausentes)}")

    def tocar(self, chave: str, loops: int = 0) -> None:
        som = self.sons.get(chave)
        if som is not None:
            som.play(loops=loops)
            self._ativos.add(chave)

    def parar(self, chave: str) -> None:
        som = self.sons.get(chave)
        if som is not None:
            som.stop()
            self._ativos.discard(chave)

    def parar_todos(self) -> None:
        for chave in list(self._ativos):
            self.parar(chave)


# ============================================================
#  DADOS E PERSISTÊNCIA
# ============================================================

CircuitoDados = dict[str, str | float]
SaveData = dict[str, Any]


class GameData:
    PASTAS_NECESSARIAS: list[str] = ["data", "sounds", "images"]
    PILOTOS_PADRAO: list[str] = [
        "Max Verstappen", "Lewis Hamilton", "Fernando Alonso",
        "Charles Leclerc", "Lando Norris",
    ]
    CIRCUITOS_PADRAO: dict[str, CircuitoDados] = {
        "1": {"nome": "Silverstone", "distancia": 5.891, "tempo_estimado": 2.2, "tipo": "pista de asfalto"},
        "2": {"nome": "Interlagos",  "distancia": 4.309, "tempo_estimado": 2.0, "tipo": "curvas técnicas"},
        "3": {"nome": "Monza",       "distancia": 5.793, "tempo_estimado": 1.8, "tipo": "alta velocidade"},
    }
    SAVE_FILE: str = "save.json"

    def __init__(self, base_dir: str) -> None:
        self.base_dir: str = base_dir
        os.chdir(base_dir)
        self.drivers_path: str = os.path.join("data", "drivers.json")
        self.circuits_path: str = os.path.join("data", "circuits.json")
        self.save_path: str = os.path.join("data", self.SAVE_FILE)

    # ---------- bootstrap ----------

    def bootstrap(self) -> None:
        for pasta in self.PASTAS_NECESSARIAS:
            if not os.path.exists(pasta):
                os.makedirs(pasta)
                print(f"📁 Pasta '{pasta}' criada automaticamente!")
        if not os.path.exists(self.drivers_path):
            self._salvar(self.drivers_path, self.PILOTOS_PADRAO)
        if not os.path.exists(self.circuits_path):
            self._salvar(self.circuits_path, self.CIRCUITOS_PADRAO)

    def load_drivers(self) -> list[str]:
        with open(self.drivers_path, "r", encoding="utf-8") as f:
            return cast(list[str], json.load(f))

    def load_circuits(self) -> dict[str, CircuitoDados]:
        with open(self.circuits_path, "r", encoding="utf-8") as f:
            return cast(dict[str, CircuitoDados], json.load(f))

    # ---------- save / load ----------

    def existe_save(self) -> bool:
        return os.path.exists(self.save_path)

    def salvar_save(
        self,
        jogador: PlayerState,
        campeonato: Championship | None = None,
        filename: str | None = None,
    ) -> None:
        caminho = os.path.join("data", filename) if filename else self.save_path

        dados: SaveData = {
            "versao": 1,
            "jogador": {
                "piloto": jogador.piloto.nome if jogador.piloto else None,
                "time":   jogador.time.nome if jogador.time else None,
                "pontos": jogador.pontos,
            },
        }
        if campeonato is not None:
            dados["campeonato"] = {
                "rodada": campeonato.rodada,
                "historico": campeonato.historico,
                "oponentes": [
                    {
                        "nome": op.nome,
                        "personalidade": op.personalidade.value,
                        "pontos": op.pontos,
                    } for op in campeonato.oponentes
                ],
            }
        self._salvar(caminho, dados)
        print(f"💾 Save gravado em {caminho}")

    def carregar_save(self, filename: str | None = None) -> SaveData | None:
        caminho = os.path.join("data", filename) if filename else self.save_path
        if not os.path.exists(caminho):
            print(f"⚠️ Nenhum save encontrado em {caminho}")
            return None
        with open(caminho, "r", encoding="utf-8") as f:
            dados = cast(SaveData, json.load(f))
        print(f"📂 Save carregado de {caminho}")
        return dados

    @staticmethod
    def _salvar(caminho: str, dados: Any) -> None:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)


# ============================================================
#  MODELOS DE DOMÍNIO
# ============================================================

class Pilot:
    def __init__(self, nome: str) -> None:
        self.nome: str = nome

    def __str__(self) -> str:
        return self.nome


class Team:
    TIMES_DISPONIVEIS: list[str] = [
        "Red Bull Racing", "Mercedes-AMG", "Ferrari", "McLaren", "Williams"
    ]

    def __init__(self, nome: str) -> None:
        self.nome: str = nome

    def __str__(self) -> str:
        return self.nome


class TireDados(dict[str, str | int]):
    """Alias só para clareza."""


class Tire:
    COMPOSTOS: dict[str, dict[str, str | int]] = {
        "1": {"nome": "Pneu Macio", "desgaste_min": 5, "desgaste_max": 9, "chance_ultrapassagem": 65},
        "2": {"nome": "Pneu Médio", "desgaste_min": 3, "desgaste_max": 5, "chance_ultrapassagem": 45},
        "3": {"nome": "Pneu Duro",  "desgaste_min": 1, "desgaste_max": 3, "chance_ultrapassagem": 25},
        "4": {"nome": "Pneu Chuva", "desgaste_min": 2, "desgaste_max": 4, "chance_ultrapassagem": 40},
    }

    def __init__(self, chave: str) -> None:
        dados = Tire.COMPOSTOS[chave]
        self.nome: str = cast(str, dados["nome"])
        self.desgaste_min: int = cast(int, dados["desgaste_min"])
        self.desgaste_max: int = cast(int, dados["desgaste_max"])
        self.chance_ultrapassagem: int = cast(int, dados["chance_ultrapassagem"])

    def desgaste_aleatorio(self) -> int:
        return random.randint(self.desgaste_min, self.desgaste_max)

    def __str__(self) -> str:
        return self.nome


class Circuit:
    def __init__(self, dados: CircuitoDados) -> None:
        self.nome: str = cast(str, dados["nome"])
        self.distancia: float = float(dados["distancia"])
        self.tempo_estimado: float = float(dados["tempo_estimado"])
        self.tipo: str = cast(str, dados["tipo"])

    def __str__(self) -> str:
        return f"{self.nome} ({self.tipo})"


# ============================================================
#  ESTADO DO CARRO E DO JOGADOR
# ============================================================

class Car:
    def __init__(self) -> None:
        self.energia: int = 100
        self.combustivel: int = 100
        self.pneus: int = 100

    def reset(self) -> None:
        self.energia = 100
        self.combustivel = 100
        self.pneus = 100

    def consumir_por_volta(self) -> None:
        self.combustivel -= random.randint(2, 5)
        self.energia -= random.randint(1, 3)

    def desgastar_pneus(self, quantidade: float) -> None:
        self.pneus -= int(quantidade)

    def reabastecer(self, quantidade: int) -> None:
        self.combustivel = min(self.combustivel + quantidade, 100)

    def trocar_pneus(self) -> None:
        self.pneus = 100

    def clampar_valores(self) -> None:
        self.combustivel = max(self.combustivel, 0)
        self.pneus = max(self.pneus, 0)
        self.energia = max(self.energia, 0)


class PlayerState:
    def __init__(self) -> None:
        self.piloto: Pilot | None = None
        self.time: Team | None = None
        self.circuito: Circuit | None = None
        self.pneu_escolhido: Tire | None = None
        self.carro: Car = Car()
        self.posicao: int = 10
        self.pontos: int = 0
        self.volta: int = 0
        self.condicao_pista: str = "Desconhecida"
        self.status_texto: str = "Aguardando Corrida"
        self.desistiu: bool = False


# ============================================================
#  IA DE OPONENTES
# ============================================================

PerfilIA = dict[str, float]

PERSONALIDADE_PERFIL: dict[Personality, PerfilIA] = {
    Personality.AGRESSIVO:    {"ataque": 1.4, "defesa": 0.8, "risco": 1.5, "desgaste": 1.3},
    Personality.CONSERVADOR:  {"ataque": 0.7, "defesa": 1.3, "risco": 0.5, "desgaste": 0.8},
    Personality.EQUILIBRADO:  {"ataque": 1.0, "defesa": 1.0, "risco": 1.0, "desgaste": 1.0},
    Personality.TALENTOSO:    {"ataque": 1.3, "defesa": 1.2, "risco": 0.9, "desgaste": 1.0},
    Personality.IMPREVISIVEL: {"ataque": 1.5, "defesa": 0.7, "risco": 2.0, "desgaste": 1.2},
}


class Opponent:
    def __init__(self, nome: str, personalidade: Personality = Personality.EQUILIBRADO) -> None:
        self.nome: str = nome
        self.personalidade: Personality = personalidade
        self.perfil: PerfilIA = PERSONALIDADE_PERFIL[personalidade]
        self.carro: Car = Car()
        self.pneu: Tire = Tire("2")
        self.posicao: int = 10
        self.pontos: int = 0
        self.desistiu: bool = False

    def reset_corrida(self, pneu_chave: str = "2") -> None:
        self.carro.reset()
        self.pneu = Tire(pneu_chave)
        self.desistiu = False

    def calcular_delta(self, volta: int, condicao_pista: str) -> int:
        if self.desistiu:
            return 0

        desgaste = self.pneu.desgaste_aleatorio() * self.perfil["desgaste"]
        if condicao_pista in ["molhado", "chuvoso"] and self.pneu.nome != "Pneu Chuva":
            desgaste *= 2.0
        elif condicao_pista == "seco" and self.pneu.nome == "Pneu Chuva":
            desgaste *= 3.0
        self.carro.desgastar_pneus(desgaste)

        if random.random() < 0.01 * self.perfil["risco"]:
            self.desistiu = True
            print(f"💥 {self.nome} abandonou a corrida!")
            return 0

        if self.carro.pneus <= 0:
            return -random.randint(1, 2)

        chance = 50 * self.perfil["ataque"]
        if condicao_pista == "seco" and self.pneu.nome == "Pneu Chuva":
            chance *= 0.5

        rolagem = random.randint(1, 100)
        if rolagem < chance:
            return random.randint(1, 2)
        if rolagem > 100 - (30 / self.perfil["defesa"]):
            return -random.randint(1, 2)
        return 0

    def __str__(self) -> str:
        return f"{self.nome} ({self.personalidade.value})"


# ============================================================
#  RENDERIZAÇÃO (PYGAME)
# ============================================================

class PygameRenderer:
    LARGURA: int = 800
    ALTURA: int = 600
    COR_FUNDO: tuple[int, int, int]    = (35, 35, 35)
    COR_TEXTO: tuple[int, int, int]    = (255, 255, 255)
    COR_DESTAQUE: tuple[int, int, int] = (255, 215, 0)
    COR_ALERTA: tuple[int, int, int]   = (255, 50, 50)
    COR_RODAPE: tuple[int, int, int]   = (200, 200, 200)

    def __init__(self) -> None:
        self.tela: pygame.Surface | None = None
        self.imagem_carro: pygame.Surface | None = None
        self.fonte_jogo: pygame.font.Font | None = None
        self.fonte_titulo: pygame.font.Font | None = None

    def inicializar(self) -> None:
        try:
            self.tela = pygame.display.set_mode((self.LARGURA, self.ALTURA))
            pygame.display.set_caption("F1 Simulator – The Real Experience")
            self.fonte_jogo = pygame.font.SysFont("Arial", 24, bold=True)
            self.fonte_titulo = pygame.font.SysFont("Arial", 32, bold=True)

            caminho_carro = os.path.join("images", "carro.png")
            if os.path.exists(caminho_carro):
                self.imagem_carro = pygame.image.load(caminho_carro)

            print("🚗 Janela gráfica e fontes iniciadas com sucesso!")
        except pygame.error as e:
            print(f"⚠️ Aviso ao abrir janela gráfica ou fontes: {e}")

    def processar_eventos(self) -> None:
        if self.tela is None:
            return
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

    def renderizar(self, jogador: PlayerState) -> None:
        if self.tela is None:
            return
        self.processar_eventos()
        self.tela.fill(self.COR_FUNDO)

        if self.imagem_carro is not None:
            rect = self.imagem_carro.get_rect(
                center=(self.LARGURA // 2, self.ALTURA // 2 + 50)
            )
            _ = self.tela.blit(self.imagem_carro, rect)

        if self.fonte_jogo is not None and self.fonte_titulo is not None:
            self._desenhar_hud(jogador)
        pygame.display.flip()

    # ---------- privados ----------

    def _desenhar_hud(self, j: PlayerState) -> None:
        assert self.fonte_jogo is not None and self.fonte_titulo is not None
        assert self.tela is not None

        nome_circuito = j.circuito.nome if j.circuito else "Nenhum"
        titulo = self.fonte_titulo.render(
            f"GP de {nome_circuito} - Volta {j.volta}/15", True, self.COR_DESTAQUE
        )
        _ = self.tela.blit(titulo, (20, 20))

        nome_piloto = j.piloto.nome if j.piloto else "Nenhum"
        nome_time = j.time.nome if j.time else "Nenhum"
        cor_pos = self.COR_DESTAQUE if j.posicao == 1 else self.COR_TEXTO

        self._blit(f"Piloto: {nome_piloto}", (20, 80))
        self._blit(f"Equipe: {nome_time}", (20, 110))
        self._blit(f"Posição: {j.posicao}º", (20, 140), cor_pos)
        self._blit(f"Pontos: {j.pontos}", (20, 170), self.COR_DESTAQUE)

        cor_pneu = self.COR_ALERTA if j.carro.pneus < 30 else self.COR_TEXTO
        cor_comb = self.COR_ALERTA if j.carro.combustivel < 25 else self.COR_TEXTO
        nome_pneu = j.pneu_escolhido.nome if j.pneu_escolhido else "Nenhum"

        self._blit(f"Pneus ({nome_pneu}): {j.carro.pneus}%", (500, 80), cor_pneu)
        self._blit(f"Combustível: {j.carro.combustivel}%", (500, 110), cor_comb)
        self._blit(f"Clima: {j.condicao_pista.upper()}", (500, 140))

        self._blit(f"Status: {j.status_texto}", (20, self.ALTURA - 40), self.COR_RODAPE)

    def _blit(
        self,
        texto: str,
        pos: tuple[int, int],
        cor: tuple[int, int, int] | None = None,
    ) -> None:
        assert self.fonte_jogo is not None and self.tela is not None
        cor_efetiva = cor if cor is not None else self.COR_TEXTO
        surf = self.fonte_jogo.render(texto, True, cor_efetiva)
        _ = self.tela.blit(surf, pos)


# ============================================================
#  CORRIDA
# ============================================================

class Race:
    TOTAL_VOLTAS: int = 15
    VOLTA_PIT_STOP: int = 8
    PONTOS_POSICAO: dict[int, int] = {
        1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
        6: 8, 7: 6, 8: 4, 9: 2, 10: 1,
    }

    def __init__(
        self,
        jogador: PlayerState,
        renderer: PygameRenderer,
        sound: SoundManager | None = None,
        oponentes: list[Opponent] | None = None,
    ) -> None:
        self.jogador: PlayerState = jogador
        self.renderer: PygameRenderer = renderer
        self.sound: SoundManager = sound if sound is not None else SoundManager()
        self.oponentes: list[Opponent] = list(oponentes) if oponentes else []
        self.erro_estrategia: bool = False
        self._chance_ultrapassagem_override: int | None = None

    # ---------- orquestração ----------

    def executar(self) -> None:
        self._preparar()
        self._loop_voltas()
        self._finalizar()

    def _preparar(self) -> None:
        j = self.jogador
        j.carro.reset()
        j.volta = 0
        j.desistiu = False
        j.status_texto = "LARGADA CONCEDIDA!"

        n = 1 + len(self.oponentes)
        posicoes: list[int] = list(range(1, n + 1))
        random.shuffle(posicoes)
        j.posicao = posicoes.pop()
        for op in self.oponentes:
            op.reset_corrida()
            op.posicao = posicoes.pop()

        assert j.circuito is not None
        print(f"\nIniciando corrida em {j.circuito.nome} com {j.pneu_escolhido}")
        print(f"Condições da pista: {j.condicao_pista}")
        print(f"Voltas previstas: {self.TOTAL_VOLTAS}")
        print(f"Grid: {n} competidores")

        self.sound.tocar("motor", loops=-1)
        self._render()
        time.sleep(2)

    def _loop_voltas(self) -> None:
        for volta in range(1, self.TOTAL_VOLTAS + 1):
            self.jogador.volta = volta
            self.jogador.status_texto = "Corrida em andamento..."
            self._render()

            self._log_estado(volta)
            self._aplicar_desgaste_jogador()

            _ = self._resolver_ultrapassagem()
            for op in self.oponentes:
                delta = op.calcular_delta(volta, self.jogador.condicao_pista)
                op.posicao = max(1, op.posicao - delta)

            if volta == self.VOLTA_PIT_STOP:
                self._pit_stop()

            if self._checar_acidente():
                break

            self._reordenar_posicoes()
            self.jogador.carro.clampar_valores()
            time.sleep(1)

    def _finalizar(self) -> None:
        self.sound.parar("motor")

        self.jogador.status_texto = "Fim de Corrida!"
        self._render()
        print("\n🏆 Corrida finalizada!")

        pontos = self.PONTOS_POSICAO.get(self.jogador.posicao, 0)
        if pontos > 0:
            print(f"Você terminou em {self.jogador.posicao}º lugar e ganhou {pontos} pontos!")
        else:
            print(f"Você terminou em {self.jogador.posicao}º lugar. Sem pontos.")

        self.sound.tocar("torcida")
        time.sleep(2)

    # ---------- lógica ----------

    def _log_estado(self, volta: int) -> None:
        c = self.jogador.carro
        print(f"\nVolta {volta}:")
        print(f"Posição: {self.jogador.posicao}º | Combustível: {c.combustivel}% "
              f"| Pneus: {c.pneus}% | Energia: {c.energia}%")

    def _aplicar_desgaste_jogador(self) -> None:
        c = self.jogador.carro
        pneu = self.jogador.pneu_escolhido
        if pneu is None:
            return
        condicao = self.jogador.condicao_pista

        c.consumir_por_volta()
        desgaste: float = float(pneu.desgaste_aleatorio())
        self.erro_estrategia = False
        self._chance_ultrapassagem_override = None

        if condicao in ["molhado", "chuvoso"] and pneu.nome != "Pneu Chuva":
            self.jogador.status_texto = "PERIGO: Carro derrapando na pista molhada!"
            desgaste *= 2.5
            self._chance_ultrapassagem_override = 10
            self.erro_estrategia = True
        elif condicao == "seco" and pneu.nome == "Pneu Chuva":
            self.jogador.status_texto = "ALERTA: Pneus superaquecendo no seco!"
            desgaste *= 3.0
            self._chance_ultrapassagem_override = 20

        c.desgastar_pneus(desgaste)

        if c.pneus <= 0:
            self.jogador.status_texto = "CRÍTICO: Pneu furado/destruído!"
            self._chance_ultrapassagem_override = 5
            self.jogador.posicao = min(self.jogador.posicao + random.randint(1, 3), 20)

    def _resolver_ultrapassagem(self) -> int:
        """Resolve a tentativa de ultrapassagem. Muta `jogador.posicao`."""
        j = self.jogador

        chance: int
        if self._chance_ultrapassagem_override is not None:
            chance = self._chance_ultrapassagem_override
        elif j.pneu_escolhido is not None:
            chance = j.pneu_escolhido.chance_ultrapassagem
        else:
            chance = 50

        rolagem = random.randint(1, 100)

        if rolagem < chance:
            if j.posicao > 1:
                ganho = random.randint(1, 2)
                j.posicao = max(j.posicao - ganho, 1)
                print("🏎️ Boa manobra! Você ganhou posições.")
                self.sound.tocar("ultrapassagem")
                return ganho
        else:
            if self.erro_estrategia or j.carro.pneus < 20 or random.random() < 0.25:
                if j.posicao < 20:
                    perda = random.randint(0, 1)
                    j.posicao = min(j.posicao + perda, 20)
                    return -perda
        return 0

    def _pit_stop(self) -> None:
        j = self.jogador
        j.status_texto = "BOX: Realizando Pit Stop..."
        self._render()
        print(f"\n🔧 PIT STOP (Volta {j.volta}): Trocando para um novo jogo de {j.pneu_escolhido}!")
        self.sound.tocar("pitstop")
        j.carro.trocar_pneus()
        j.carro.reabastecer(30)
        time.sleep(1.5)

    def _checar_acidente(self) -> bool:
        chance = 0.05 if self.erro_estrategia else 0.01
        if random.random() < chance:
            j = self.jogador
            j.status_texto = "💥 ACIDENTE! Fim de prova para você."
            j.desistiu = True
            j.posicao = 20
            self._render()
            print("💥 Rodou! Você colidiu devido à falta de aderência!")
            self.sound.tocar("batida")
            time.sleep(2)
            return True
        return False

    def _reordenar_posicoes(self) -> None:
        todos: list[PlayerState | Opponent] = [self.jogador, *self.oponentes]
        ativos: list[PlayerState | Opponent] = [r for r in todos if not r.desistiu]
        desistentes: list[PlayerState | Opponent] = [r for r in todos if r.desistiu]

        random.shuffle(ativos)
        ativos.sort(key=lambda r: r.posicao)

        for i, r in enumerate(ativos, start=1):
            r.posicao = i
        for i, r in enumerate(desistentes, start=len(ativos) + 1):
            r.posicao = i

    def _render(self) -> None:
        self.renderer.renderizar(self.jogador)


# ============================================================
#  CAMPEONATO
# ============================================================

HistoricoItem = dict[str, str | int]
EntradaClassificacao = tuple[str, int, str]


class Championship:
    def __init__(
        self,
        jogador: PlayerState,
        oponentes: list[Opponent],
        calendario: list[Circuit],
        renderer: PygameRenderer,
        sound: SoundManager,
        game_data: GameData,
    ) -> None:
        self.jogador: PlayerState = jogador
        self.oponentes: list[Opponent] = oponentes
        self.calendario: list[Circuit] = calendario
        self.renderer: PygameRenderer = renderer
        self.sound: SoundManager = sound
        self.game_data: GameData = game_data
        self.rodada: int = 0
        self.historico: list[HistoricoItem] = []

    def executar(self, pedir_pneu_callback: Callable[[], Tire]) -> None:
        for i, circuito in enumerate(self.calendario, start=1):
            self.rodada = i
            print(f"\n{'=' * 55}")
            print(f"🏁 RODADA {i}/{len(self.calendario)} — {circuito.nome}")
            print(f"{'=' * 55}")

            self.jogador.circuito = circuito
            self.jogador.condicao_pista = random.choice(["seco", "molhado", "chuvoso"])
            self.jogador.pneu_escolhido = pedir_pneu_callback()

            corrida = Race(self.jogador, self.renderer, self.sound, self.oponentes)
            corrida.executar()

            self._registrar_resultado(circuito)
            self._mostrar_classificacao()
            self.game_data.salvar_save(self.jogador, campeonato=self)

        self._mostrar_classificacao_final()

    def _registrar_resultado(self, circuito: Circuit) -> None:
        pontos_jogador = Race.PONTOS_POSICAO.get(self.jogador.posicao, 0)
        self.jogador.pontos += pontos_jogador
        self.historico.append({
            "circuito": circuito.nome,
            "posicao": self.jogador.posicao,
            "pontos": pontos_jogador,
        })
        for op in self.oponentes:
            op.pontos += Race.PONTOS_POSICAO.get(op.posicao, 0)

    def classificacao(self) -> list[EntradaClassificacao]:
        entradas: list[EntradaClassificacao] = []
        if self.jogador.piloto is not None:
            entradas.append((self.jogador.piloto.nome, self.jogador.pontos, "jogador"))
        for op in self.oponentes:
            entradas.append((op.nome, op.pontos, "oponente"))
        return sorted(entradas, key=lambda x: x[1], reverse=True)

    def _mostrar_classificacao(self) -> None:
        print(f"\n📊 Classificação após rodada {self.rodada}:")
        for i, (nome, pontos, tipo) in enumerate(self.classificacao(), start=1):
            marca = "  ← você" if tipo == "jogador" else ""
            print(f"  {i:2d}. {nome:25s} {pontos:3d} pts{marca}")

    def _mostrar_classificacao_final(self) -> None:
        print("\n" + "=" * 55)
        print("🏆 CAMPEONATO ENCERRADO")
        print("=" * 55)
        self._mostrar_classificacao()
        vencedor = self.classificacao()[0]
        print(f"\n🥇 Campeão: {vencedor[0]} com {vencedor[1]} pontos!")


# ============================================================
#  CONTROLADOR PRINCIPAL
# ============================================================

class F1Simulator:
    def __init__(self) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data: GameData = GameData(base_dir)
        self.data.bootstrap()

        _ = pygame.init()
        _ = pygame.mixer.init()

        self.renderer: PygameRenderer = PygameRenderer()
        self.renderer.inicializar()

        self.sound: SoundManager = SoundManager()

        self.pilotos_lista: list[str] = self.data.load_drivers()
        self.circuits_dados: dict[str, CircuitoDados] = self.data.load_circuits()
        self.circuitos_obj: dict[str, Circuit] = {
            k: Circuit(v) for k, v in self.circuits_dados.items()
        }

        self.jogador: PlayerState = PlayerState()
        self.oponentes: list[Opponent] = []

    # ---------- loop do menu ----------

    def executar(self) -> None:
        while True:
            escolha = self._mostrar_menu()
            if not self._processar_escolha(escolha):
                break

    def _mostrar_menu(self) -> str:
        self.jogador.status_texto = "Aguardando comandos no terminal..."
        self.renderer.renderizar(self.jogador)

        print("\n=== F1 Simulator - The Real Experience ===")
        print("1. Escolher piloto")
        print("2. Escolher time")
        print("3. Escolher circuito")
        print("4. Corrida única")
        print("5. Campeonato (todos os circuitos)")
        print("6. Carregar save")
        print("7. Sair")
        return input("Escolha uma opção: ")

    def _processar_escolha(self, escolha: str) -> bool:
        try:
            if escolha == "1":
                self.jogador.piloto = self._escolher_piloto()
                print(f"Piloto escolhido: {self.jogador.piloto}")
            elif escolha == "2":
                self.jogador.time = self._escolher_time()
                print(f"Time escolhido: {self.jogador.time}")
            elif escolha == "3":
                self.jogador.circuito = self._escolher_circuito()
                print(f"Circuito: {self.jogador.circuito}")
            elif escolha == "4":
                self._iniciar_corrida_unica()
            elif escolha == "5":
                self._iniciar_campeonato()
            elif escolha == "6":
                self._carregar_save()
            elif escolha == "7":
                print("Obrigado por jogar!")
                pygame.quit()
                return False
            else:
                print("Opção inválida!")
        except (ValueError, IndexError, KeyError) as e:
            print(f"❌ Entrada inválida: {e}")
        return True

    # ---------- sub-menus ----------

    def _escolher_piloto(self) -> Pilot:
        print("\nEscolha seu piloto:")
        for idx, p in enumerate(self.pilotos_lista, 1):
            print(f"{idx}. {p}")
        escolha = int(input("Digite o número do piloto: ")) - 1
        return Pilot(self.pilotos_lista[escolha])

    def _escolher_time(self) -> Team:
        print("\nEscolha seu time:")
        for idx, t in enumerate(Team.TIMES_DISPONIVEIS, 1):
            print(f"{idx}. {t}")
        escolha = int(input("Digite o número do time: ")) - 1
        return Team(Team.TIMES_DISPONIVEIS[escolha])

    def _escolher_circuito(self) -> Circuit:
        print("\nEscolha o circuito:")
        for key, c in self.circuitos_obj.items():
            print(f"{key}. {c}")
        escolha = input("Digite o número: ")
        return self.circuitos_obj[escolha]

    def _escolher_pneu(self) -> Tire:
        print("\nEscolha seu tipo de pneu:")
        for key, dados in Tire.COMPOSTOS.items():
            nome = cast(str, dados["nome"])
            print(f"{key}. {nome}")
        escolha = input("Digite o número: ")
        return Tire(escolha)

    # ---------- fluxo de corrida ----------

    def _validar_prerequisitos(self) -> bool:
        if not self.jogador.piloto or not self.jogador.time:
            print("❌ Erro: Escolha um piloto (1) e um time (2) antes!")
            return False
        return True

    def _iniciar_corrida_unica(self) -> None:
        if not self._validar_prerequisitos():
            return
        if self.jogador.circuito is None:
            print("❌ Erro: Escolha um circuito (Opção 3) antes!")
            return
        self._preparar_oponentes()
        self.jogador.condicao_pista = random.choice(["seco", "molhado", "chuvoso"])
        self.jogador.pneu_escolhido = self._escolher_pneu()

        corrida = Race(self.jogador, self.renderer, self.sound, self.oponentes)
        corrida.executar()
        self.data.salvar_save(self.jogador)

    def _iniciar_campeonato(self) -> None:
        if not self._validar_prerequisitos():
            return
        self._preparar_oponentes()

        calendario = list(self.circuitos_obj.values())
        campeonato = Championship(
            self.jogador, self.oponentes, calendario,
            self.renderer, self.sound, self.data,
        )
        campeonato.executar(pedir_pneu_callback=self._escolher_pneu)

    def _preparar_oponentes(self) -> None:
        nomes: list[tuple[str, Personality]] = [
            ("Lewis Hamilton",   Personality.TALENTOSO),
            ("Charles Leclerc",  Personality.AGRESSIVO),
            ("Lando Norris",     Personality.IMPREVISIVEL),
            ("Carlos Sainz",     Personality.EQUILIBRADO),
            ("George Russell",   Personality.CONSERVADOR),
            ("Sergio Perez",     Personality.AGRESSIVO),
            ("Fernando Alonso",  Personality.EQUILIBRADO),
            ("Esteban Ocon",     Personality.CONSERVADOR),
            ("Pierre Gasly",     Personality.IMPREVISIVEL),
        ]
        nome_jogador = self.jogador.piloto.nome if self.jogador.piloto else None
        self.oponentes = [Opponent(n, p) for n, p in nomes if n != nome_jogador]

    # ---------- save ----------

    def _carregar_save(self) -> None:
        dados = self.data.carregar_save()
        if dados is None:
            return

        j = cast(dict[str, Any], dados.get("jogador", {}))
        if j.get("piloto"):
            self.jogador.piloto = Pilot(cast(str, j["piloto"]))
        if j.get("time"):
            self.jogador.time = Team(cast(str, j["time"]))
        self.jogador.pontos = cast(int, j.get("pontos", 0))

        print(f"📊 Piloto: {self.jogador.piloto} | "
              f"Time: {self.jogador.time} | Pontos: {self.jogador.pontos}")

        camp_raw = dados.get("campeonato")
        if isinstance(camp_raw, dict):
            camp = cast(dict[str, Any], camp_raw)
            rodada = cast(int, camp.get("rodada", 0))
            print(f"🏁 Campeonato salvo — rodada {rodada}")

            historico_raw = camp.get("historico", [])
            if isinstance(historico_raw, list):
                historico = cast(list[Any], historico_raw)
                for item_raw in historico:
                    if isinstance(item_raw, dict):
                        item = cast(dict[str, Any], item_raw)
                        print(f"   • {item['circuito']}: P{item['posicao']} "
                              f"({item['pontos']} pts)")


# ============================================================
#  ENTRY POINT
# ============================================================

if __name__ == "__main__":
    F1Simulator().executar()