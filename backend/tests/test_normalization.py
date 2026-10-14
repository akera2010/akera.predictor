from akeraten.data_ingestion import merge_matches
from akeraten.data_ingestion.apify_flashscore_tt import ApifyFlashscoreTTClient
from akeraten.data_ingestion.apify_sofascore import ApifySofascoreClient
from akeraten.data_ingestion.betfair import BetfairClient
from akeraten.data_ingestion.extra_apis import GenericClient, load_extra_apis
from akeraten.data_ingestion.livetennisapi import LiveTennisAPIClient
from akeraten.data_ingestion.schema import norm_status, norm_surface
from akeraten.data_ingestion.sportapi_net import SportAPINetClient
from akeraten.data_ingestion.sportmicro import SportMicroClient
from akeraten.data_ingestion.sportradar_tt import SportradarTTClient
from akeraten.data_ingestion.the_odds_api import TheOddsAPIClient

REQUIRED = {"sport", "match_id", "player_a", "player_b", "tournament", "surface", "status", "score", "odds",
            "timestamp", "source"}


def check(m, sport):
    assert m and REQUIRED <= set(m)
    assert m["sport"] == sport
    assert m["status"] in ("live", "upcoming", "finished")
    assert set(m["score"]) >= {"sets", "games", "points"}


def test_livetennisapi():
    it = {"id": 7, "home": {"name": "Jannik Sinner", "rank": 2}, "away": {"name": "Carlos Alcaraz", "rank": 1},
          "tournament": {"name": "ATP Vienna", "surface": "Hard (indoor)", "category": "ATP"}, "status": "live",
          "score": {"sets": [{"home": 6, "away": 4}, {"home": 3, "away": 2}], "points": {"home": "30", "away": "15"},
                    "server": "home"}, "odds": {"home": 1.85, "away": 2.05}}
    m = LiveTennisAPIClient().normalize(it)
    check(m, "tennis")
    assert m["score"]["sets"] == [[6, 4], [3, 2]] and m["score"]["points"] == "30-15"
    assert m["surface"] == "indoor" and m["server"] == "a" and m["odds"]["player_a"] == 1.85


def test_sportradar_tt():
    it = {"sport_event": {"id": "sr:sport_event:1", "start_time": "2026-10-14T10:00:00+00:00",
                          "sport_event_context": {"competition": {"name": "WTT Champions"}},
                          "competitors": [{"name": "Wang, Chuqin", "qualifier": "home", "country_code": "CHN"},
                                          {"name": "Calderano, Hugo", "qualifier": "away", "country_code": "BRA"}]},
          "sport_event_status": {"status": "live", "home_score": 1, "away_score": 0,
                                 "period_scores": [{"home_score": 11, "away_score": 8},
                                                   {"home_score": 5, "away_score": 3}]}}
    m = SportradarTTClient().normalize(it)
    check(m, "table_tennis")
    assert m["player_a"] == "Wang Chuqin" and m["player_b"] == "Hugo Calderano"
    assert m["score"]["games"] == [1, 0] and m["score"]["points"] == "5-3" and m["category"] == "WTT"


def test_apify_flashscore_tt():
    it = {"matchId": "abc", "homeName": "Sun Yingsha", "awayName": "Wang Manyu", "tournament": "WTT China Smash",
          "status": "finished", "homeScore": 3, "awayScore": 1, "sets": [{"home": 11, "away": 7}],
          "odds": {"home": 1.5, "away": 2.6}}
    m = ApifyFlashscoreTTClient().normalize(it)
    check(m, "table_tennis")
    assert m["status"] == "finished" and m["odds"] == {"player_a": 1.5, "player_b": 2.6}


SOFA = {"id": 99, "homeTeam": {"name": "Iga Swiatek", "ranking": 2}, "awayTeam": {"name": "Coco Gauff", "ranking": 3},
        "tournament": {"name": "WTA Wuhan", "category": {"name": "WTA", "sport": {"slug": "tennis"}}},
        "status": {"type": "inprogress"}, "homeScore": {"period1": 6, "period2": 2, "point": "40"},
        "awayScore": {"period1": 3, "period2": 2, "point": "A"}, "groundType": "Hardcourt outdoor", "firstToServe": 2,
        "startTimestamp": 1760436000}


def test_apify_sofascore():
    m = ApifySofascoreClient().normalize(SOFA)
    check(m, "tennis")
    assert m["score"]["sets"] == [[6, 3], [2, 2]] and m["score"]["points"] == "40-A"
    assert m["surface"] == "hard" and m["category"] == "WTA" and m["start_time"].endswith("Z")


def test_sportmicro_tt():
    ev = {"id": 5, "homeTeam": {"name": "Lin Shidong"}, "awayTeam": {"name": "Truls Moregard"},
          "tournament": {"name": "WTT Star Contender", "category": {"sport": {"slug": "table-tennis"}}},
          "status": {"type": "inprogress"}, "homeScore": {"current": 2, "period1": 11, "period2": 9, "period3": 4},
          "awayScore": {"current": 0, "period1": 6, "period2": 11, "period3": 2}}
    m = SportMicroClient().normalize(ev)
    check(m, "table_tennis")
    assert m["score"]["points"] == "4-2" and m["category"] == "WTT"


def test_sportapi_net():
    it = {"id": 1, "sport": "tennis", "league": {"name": "ATP Basel", "category": "ATP"},
          "participants": [{"name": "Taylor Fritz", "side": "home"}, {"name": "Ben Shelton", "side": "away"}],
          "status": "upcoming", "scores": {}, "odds": {"home": 1.7, "away": 2.2}, "surface": "indoor"}
    m = SportAPINetClient().normalize(it)
    check(m, "tennis")
    assert m["status"] == "upcoming" and m["surface"] == "indoor"


def test_the_odds_api():
    ev = {"id": "e1", "sport_title": "ATP Vienna", "commence_time": "2099-01-01T10:00:00Z", "home_team": "Jannik Sinner",
          "away_team": "Alexander Zverev", "bookmakers": [
              {"key": "bwin", "title": "Bwin", "markets": [{"key": "h2h", "outcomes": [
                  {"name": "Jannik Sinner", "price": 1.3}, {"name": "Alexander Zverev", "price": 3.5}]}]},
              {"key": "pinnacle", "title": "Pinnacle", "markets": [{"key": "h2h", "outcomes": [
                  {"name": "Alexander Zverev", "price": 3.6}, {"name": "Jannik Sinner", "price": 1.32}]}]}]}
    m = TheOddsAPIClient().normalize(ev)
    check(m, "tennis")
    assert m["odds"] == {"player_a": 1.32, "player_b": 3.6} and m["bookmaker"] == "Pinnacle"
    assert m["status"] == "upcoming"


def test_betfair():
    it = {"sport": "tennis",
          "catalogue": {"marketId": "1.23", "competition": {"name": "ATP Basel"}, "marketStartTime": "2026-10-20T10:00:00Z",
                        "runners": [{"selectionId": 1, "runnerName": "Casper Ruud"},
                                    {"selectionId": 2, "runnerName": "Holger Rune"}]},
          "book": {"inplay": True, "status": "OPEN", "runners": [
              {"selectionId": 1, "ex": {"availableToBack": [{"price": 2.2, "size": 100}]}},
              {"selectionId": 2, "ex": {"availableToBack": [{"price": 1.8, "size": 100}]}}]}}
    m = BetfairClient().normalize(it)
    check(m, "tennis")
    assert m["status"] == "live" and m["odds"] == {"player_a": 2.2, "player_b": 1.8}


def test_generic_extra_api():
    c = GenericClient({"name": "feed", "base_url": "https://x.invalid", "sport": ["tennis"], "auth": {"type": "none"},
                       "mapping": {"match_id": "id", "player_a": "h.n", "player_b": "a.n", "odds_a": "o.0",
                                   "odds_b": "o.1"}})
    m = c.normalize({"id": 3, "h": {"n": "Paula Badosa"}, "a": {"n": "Jessica Pegula"}, "o": [2.5, 1.55],
                     "status": "live", "score": {"sets": [[4, 6], [1, 0]], "points": "15-0"}})
    check(m, "tennis")
    assert m["match_id"] == "feed-3" and m["odds"]["player_b"] == 1.55
    assert all(isinstance(x, GenericClient) for x in load_extra_apis())


def test_clients_without_key_are_skipped(monkeypatch):
    for k in ("LIVETENNISAPI_KEY", "ODDS_API_KEY", "BETFAIR_APP_KEY"):
        monkeypatch.delenv(k, raising=False)
    for cls in (LiveTennisAPIClient, TheOddsAPIClient, BetfairClient):
        c = cls()
        assert not c.enabled
        assert c.fetch() == [] and c.status == "disabled"


def test_status_surface_normalisers():
    assert norm_status("inprogress") == "live" and norm_status("Ended") == "finished"
    assert norm_status("notstarted") == "upcoming"
    assert norm_surface("Red clay") == "clay" and norm_surface("Grass") == "grass" and norm_surface(None) is None


def test_merge_scores_and_odds_swapped():
    a = LiveTennisAPIClient().normalize({"id": 1, "home": {"name": "Jannik Sinner"}, "away": {"name": "Carlos Alcaraz"},
                                         "tournament": {"name": "ATP"}, "status": "live", "score": {"sets": []}})
    b = TheOddsAPIClient().normalize({"id": "x", "home_team": "Alcaraz C.", "away_team": "Sinner J.",
                                      "commence_time": "2000-01-01T00:00:00Z", "bookmakers": [
                                          {"key": "pinnacle", "title": "Pinnacle", "markets": [{"key": "h2h", "outcomes": [
                                              {"name": "Alcaraz C.", "price": 1.9}, {"name": "Sinner J.", "price": 1.95}]}]}]})
    merged = merge_matches([[a], [b]])
    assert len(merged) == 1
    assert merged[0]["odds"] == {"player_a": 1.95, "player_b": 1.9}
    assert set(merged[0]["sources"]) == {"livetennisapi", "the_odds_api"}
