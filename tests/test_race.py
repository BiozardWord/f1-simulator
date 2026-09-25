# pyright: strict
"""Testes unitários com tipagem estrita."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from f1_simulator import (
    Opponent, Personality, PlayerState, PygameRenderer, Race, SoundManager, Tire,
)


def make_race(
    posicao: int = 10,
    pneus: int = 100,
    chance_override: int | None = None,
    erro: bool = False,
) -> Race:
    jogador = PlayerState()
    jogador.carro.pneus = pneus
    jogador.posicao = posicao
    jogador.pneu_escolhido = Tire("2")

    renderer: PygameRenderer = MagicMock(spec=PygameRenderer)
    sound: SoundManager = MagicMock(spec=SoundManager)

    race = Race(jogador, renderer, sound=sound, oponentes=[])
    race._chance_ultrapassagem_override = chance_override  # type: ignore[reportPrivateUsage]
    race.erro_estrategia = erro
    return race


class TestResolverUltrapassagem:
    def test_sucesso_move_para_cima(self) -> None:
        race = make_race(posicao=10)
        with patch("f1_simulator.random.randint", side_effect=[1, 2]):
            delta = race._resolver_ultrapassagem()  # type: ignore[reportPrivateUsage]
        assert delta == 2
        assert race.jogador.posicao == 8

    def test_primeiro_lugar_nao_pode_ultrapassar(self) -> None:
        race = make_race(posicao=1)
        with patch("f1_simulator.random.randint", side_effect=[1]):
            delta = race._resolver_ultrapassagem()  # type: ignore[reportPrivateUsage]
        assert delta == 0
        assert race.jogador.posicao == 1

    def test_falha_sem_penalidade_nao_move(self) -> None:
        race = make_race(posicao=5, pneus=100, erro=False)
        with patch("f1_simulator.random.randint", side_effect=[99]), \
             patch("f1_simulator.random.random", return_value=0.99):
            delta = race._resolver_ultrapassagem()  # type: ignore[reportPrivateUsage]
        assert delta == 0
        assert race.jogador.posicao == 5

    def test_falha_com_erro_estrategia_perde_posicao(self) -> None:
        race = make_race(posicao=5, erro=True)
        with patch("f1_simulator.random.randint", side_effect=[99, 1]):
            delta = race._resolver_ultrapassagem()  # type: ignore[reportPrivateUsage]
        assert delta == -1
        assert race.jogador.posicao == 6

    def test_falha_com_pneu_destruido_perde_posicao(self) -> None:
        race = make_race(posicao=5, pneus=10, erro=False)
        with patch("f1_simulator.random.randint", side_effect=[99, 1]):
            delta = race._resolver_ultrapassagem()  # type: ignore[reportPrivateUsage]
        assert delta == -1
        assert race.jogador.posicao == 6

    def test_pneu_destruido_mas_ultimo_lugar_nao_passa_de_20(self) -> None:
        race = make_race(posicao=20, pneus=5, erro=False)
        with patch("f1_simulator.random.randint", side_effect=[99, 1]):
            _ = race._resolver_ultrapassagem()  # type: ignore[reportPrivateUsage]
        assert race.jogador.posicao == 20

    def test_override_de_chance_e_respeitado(self) -> None:
        race = make_race(posicao=10, chance_override=10)
        with patch("f1_simulator.random.randint", side_effect=[5, 1]):
            delta = race._resolver_ultrapassagem()  # type: ignore[reportPrivateUsage]
        assert delta == 1
        assert race.jogador.posicao == 9

    def test_override_baixo_bloqueia_ultrapassagem(self) -> None:
        race = make_race(posicao=10, chance_override=5, pneus=100)
        with patch("f1_simulator.random.randint", side_effect=[50]), \
             patch("f1_simulator.random.random", return_value=0.99):
            delta = race._resolver_ultrapassagem()  # type: ignore[reportPrivateUsage]
        assert delta == 0
        assert race.jogador.posicao == 10


class TestOpponent:
    def test_agressivo_ataca_mais_que_conservador(self) -> None:
        op_agr = Opponent("A", Personality.AGRESSIVO)
        op_con = Opponent("B", Personality.CONSERVADOR)
        assert op_agr.perfil["ataque"] > op_con.perfil["ataque"]
        assert op_agr.perfil["risco"] > op_con.perfil["risco"]

    def test_abandono_quando_sorteia_acidente(self) -> None:
        op = Opponent("A", Personality.AGRESSIVO)
        with patch("f1_simulator.random.random", return_value=0.0):
            delta = op.calcular_delta(volta=1, condicao_pista="seco")
        assert op.desistiu is True
        assert delta == 0

    def test_desistente_nao_muda_posicao(self) -> None:
        op = Opponent("A", Personality.CONSERVADOR)
        op.desistiu = True
        delta = op.calcular_delta(volta=5, condicao_pista="seco")
        assert delta == 0