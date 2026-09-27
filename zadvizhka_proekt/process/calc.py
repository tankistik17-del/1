# -*- coding: utf-8 -*-
"""
Эталонный расчёт: техпроцесс сборки-сварки корпуса (операции 020–050) и экономика участка.

  python3 calc.py        -> печать таблиц и out/economics.json (исходные данные, швы, результаты)

Страница process/ повторяет эти формулы на JS; значения должны совпасть.
Геометрия швов и массы деталей — из модели корпуса (korpus/build.py).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
RHO = 7.85e-3            # г/мм³, сталь

# ---------------------------------------------------------------------------
# Исходные данные: значение, единица, подпись, источник/допущение
# ---------------------------------------------------------------------------
P = {
    # режим (лист 5)
    "I": (134, "А", "Сварочный ток", "лист 5, операции 020–040"),
    "U": (23, "В", "Напряжение дуги", "лист 5"),
    "vsv": (46, "м/ч", "Скорость сварки", "лист 5"),
    "eta_src": (0.70, "", "КПД источника ВС-300Б (с учётом cos φ)", "допущение, паспортные данные выпрямителей"),
    "p_idle": (0.4, "кВт", "Мощность холостого хода поста", "допущение"),
    "gas_lpm": (13, "л/мин", "Расход защитного газа", "типовой 12–15 л/мин для Ø1,2 мм"),
    "psi": (0.10, "", "Потери проволоки на разбрызгивание и огарки", "типовые 5–15% для сварки в смеси"),
    "k_reinf": (1.15, "", "Коэффициент усиления шва к сечению катета", "с учётом выпуклости шва"),
    # нормирование, мин на корпус (вспомогательное время по операциям)
    "tv_020": (2.5, "мин", "Tв 020: установка стакана и 2 направляющих, зажим, 8 прихваток, поворот, снятие", "допущение по общемашиностроительным нормативам"),
    "tv_025": (1.5, "мин", "Tв 025: установка фланца на палец и п/сб.1, зажим, снятие", "допущение"),
    "tv_030": (1.2, "мин", "Tв 030: установка дна, прихватка, снятие", "допущение"),
    "tv_035": (1.0, "мин", "Tв 035: установка фланца на патрубок, прихватка, снятие (на 1 п/сб.4)", "допущение"),
    "tv_040": (3.0, "мин", "Tв 040: сборка п/сб.3 + 2 п/сб.4, контроль 34±1, прихватки, повороты", "допущение"),
    "t_045": (6.0, "мин", "Операция 045: зачистка швов шлифмашиной, осмотр", "допущение"),
    "t_050": (10.0, "мин", "Операция 050: контроль и гидроиспытание 1,6 МПа (заполнение, выдержка, слив)", "допущение"),
    "a_obs": (12, "%", "Время на обслуживание рабочего места, отдых и личные надобности", "нормативы для сварки в CO₂: 10–15%"),
    # цены
    "c_pipe": (130, "₽/кг", "Труба бесшовная ст.20 (патрубки, стакан)", "≈130 тыс. ₽/т, прайсы металлобаз 2026 (Inrost, Трубпром)"),
    "c_bar": (100, "₽/кг", "Квадрат 14 и лист 5 мм ст.20 (направляющие, дно)", "допущение, сортовой и листовой прокат"),
    "c_flange": (1000, "₽/шт", "Фланец Ø210 (заготовка-аналог фланца Ду100 Ру16)", "903–1204 ₽ за фланец Ду100 Ру16 ГОСТ 33259, 2026"),
    "kim_pipe": (0.85, "", "КИМ трубы (резка, торцевание)", "допущение"),
    "kim_bar": (0.95, "", "КИМ квадрата", "допущение"),
    "kim_sheet": (0.70, "", "КИМ листа для дна (круглая вырубка)", "допущение"),
    "c_wire": (210, "₽/кг", "Проволока Св-08Г2С Ø1,2 (кассета 18 кг)", "КЕДР 210 ₽/кг, ESAB 213 ₽/кг, 2026"),
    "c_gas": (2562, "₽/баллон", "Смесь К-25 (Ar 75% + CO₂ 25%), баллон 40 л", "УралКриоГаз, 2026"),
    "v_gas": (6.0, "м³/баллон", "Объём газа в баллоне 40 л при 15 МПа", "справочно ≈ 6 м³"),
    "c_kwh": (9.0, "₽/кВт·ч", "Электроэнергия для предприятия", "допущение, средний нерегулируемый тариф 2026"),
    # труд
    "sal_w": (100000, "₽/мес", "Зарплата сварщика (с премией)", "медиана 98 тыс. ₽, ГородРабот 2026"),
    "h_month": (164.4, "ч/мес", "Среднемесячный фонд рабочего времени", "производственный календарь, 40-ч неделя"),
    "ins": (30, "%", "Страховые взносы", "общий тариф"),
    # постоянные затраты, ₽/год
    "n_posts": (6, "шт", "Число сварочных постов", "лист 9"),
    "c_post": (240000, "₽", "Оборудование поста: ВС-300Б + ПДГ-312-5 + горелка", "165–171 тыс. + 59 тыс. + ≈15 тыс., 2026"),
    "c_fix": (300000, "₽", "Приспособление (изготовление), за 1 шт", "допущение"),
    "n_fix": (4, "шт", "Приспособлений №1 и №2 на участке", "допущение: по 2 шт"),
    "c_stand": (400000, "₽", "Стенд гидроиспытаний", "допущение"),
    "c_vent": (60000, "₽", "Местная вентиляция на пост", "допущение"),
    "am_eq": (10, "%/год", "Норма амортизации оборудования", "срок службы 10 лет"),
    "am_fix": (20, "%/год", "Норма амортизации приспособлений", "срок службы 5 лет"),
    "area": (648, "м²", "Площадь участка", "лист 9: 36 × 18 м"),
    "c_area": (6000, "₽/(м²·год)", "Содержание (аренда) площади", "допущение, ≈500 ₽/м² в месяц"),
    "sal_m": (120000, "₽/мес", "Зарплата мастера участка", "допущение"),
    "n_m": (2, "чел", "Мастеров (по одному в смену)", "лист 9: стол мастера"),
    "other": (300000, "₽/год", "Прочие цеховые расходы", "допущение"),
    # мощность и программа
    "days": (247, "дн", "Рабочих дней в году", "производственный календарь 2026"),
    "shifts": (2, "", "Смен", "допущение"),
    "h_shift": (8, "ч", "Длительность смены", ""),
    "k_rep": (5, "%", "Потери на ремонт оборудования", "допущение"),
    "n_ctrl": (1, "шт", "Мест контроля и гидроиспытания", "лист 9: стол контролёра"),
    "load": (80, "%", "Загрузка участка", "принято"),
    "rent": (20, "%", "Рентабельность (наценка к полной себестоимости)", "принято"),
}
V = {k: v[0] for k, v in P.items()}

# ---------------------------------------------------------------------------
# Швы: траектории (центр валика) и длины. Кадры модели: X — проход, Z — стакан.
# ---------------------------------------------------------------------------


def saddle_pts(sgn, n=96, r=56.5, R=66.0):
    return [[sgn * math.sqrt(max(R*R - (r*math.cos(t))**2, 0)), r*math.cos(t), r*math.sin(t)]
            for t in [2*math.pi*i/n for i in range(n+1)]]


def ring_pts(axis, c, r, n=96):
    out = []
    for i in range(n+1):
        t = 2*math.pi*i/n
        a, b = r*math.cos(t), r*math.sin(t)
        out.append([c, a, b] if axis == "x" else [a, b, c])
    return out


def plen(pts):
    return sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))


WELDS = []
for i, (x, y, z0, z1) in enumerate([(-8, 56.5, 92, 132), (-8, 56.5, -60, -20), (8, 56.5, 92, 132), (8, 56.5, -60, -20),
                                    (-8, -56.5, 92, 132), (-8, -56.5, -60, -20), (8, -56.5, 92, 132), (8, -56.5, -60, -20)], 1):
    WELDS.append(dict(key="shov_1_%d" % i, op="020", pts=[[x, y, z0], [x, y, z1]]))
WELDS.append(dict(key="shov_2_1_stakan_flanec", op="025", pts=ring_pts("z", 129.0, 66.0)))
WELDS.append(dict(key="shov_3_dno_stakan", op="030", pts=ring_pts("z", -69.5, 65.5)))
WELDS.append(dict(key="shov_2_2_patrubok_flanec_L", op="035", pts=ring_pts("x", -86.0, 56.5)))
WELDS.append(dict(key="shov_2_3_patrubok_flanec_R", op="035", pts=ring_pts("x", 86.0, 56.5)))
WELDS.append(dict(key="shov_2_4_patrubok_stakan_L", op="040", pts=saddle_pts(-1)))
WELDS.append(dict(key="shov_2_5_patrubok_stakan_R", op="040", pts=saddle_pts(1)))
for w in WELDS:
    w["L"] = plen(w["pts"])

# объёмы тел швов и массы деталей из модели корпуса
sys.path.insert(0, os.path.join(PROJ, "korpus"))
import io, contextlib  # noqa: E401,E402
with contextlib.redirect_stdout(io.StringIO()):
    from build import make_korpus_parts  # noqa: E402
    PARTS = {k: wp.val().Volume() for k, _n, wp, _c in make_korpus_parts()}
for w in WELDS:
    w["V"] = PARTS[w["key"]]


def compute(V, WELDS, PARTS):
    vsv = V["vsv"] * 1000 / 60                         # мм/мин
    ops = {}
    for op, tv in [("020", "tv_020"), ("025", "tv_025"), ("030", "tv_030"), ("035", "tv_035"), ("040", "tv_040")]:
        L = sum(w["L"] for w in WELDS if w["op"] == op)
        to = L / vsv
        n = 2 if op == "035" else 1                    # 035 выполняется дважды (два п/сб.4)
        tv = V[tv] * n
        ops[op] = dict(L=L, to=to, tv=tv, tsh=(to + tv) * (1 + V["a_obs"]/100))
    ops["045"] = dict(L=0, to=0, tv=V["t_045"], tsh=V["t_045"] * (1 + V["a_obs"]/100))
    ops["050"] = dict(L=0, to=0, tv=V["t_050"], tsh=V["t_050"] * (1 + V["a_obs"]/100))
    to_sum = sum(o["to"] for o in ops.values())
    L_sum = sum(o["L"] for o in ops.values())
    t_weld_posts = sum(ops[k]["tsh"] for k in ("020", "025", "030", "035", "040", "045"))   # на сварочных постах
    t_ctrl = ops["050"]["tsh"]
    t_all = t_weld_posts + t_ctrl

    # материалы, ₽/шт
    m = lambda k: PARTS[k] * RHO / 1000                # кг
    m_pipe = m("01_patrubok_L") + m("01_patrubok_R") + m("02_stakan")
    m_bar = m("05_napravlyayushchaya_1") + m("05_napravlyayushchaya_2")
    m_sheet = m("06_dno")
    mat = dict(
        pipe=m_pipe / V["kim_pipe"] * V["c_pipe"],
        bar=m_bar / V["kim_bar"] * V["c_bar"],
        sheet=m_sheet / V["kim_sheet"] * V["c_bar"],
        flange=3 * V["c_flange"],
    )
    v_dep = sum(w["V"] for w in WELDS)                 # мм³, сечение катета без усиления
    g_wire = v_dep * RHO / 1000 * V["k_reinf"] * (1 + V["psi"])    # кг
    gas_l = V["gas_lpm"] * to_sum * 1.1                # + продувка до/после
    kwh = (V["U"] * V["I"] / 1000 / V["eta_src"]) * to_sum / 60 + V["p_idle"] * (t_weld_posts - to_sum) / 60
    rate = V["sal_w"] / V["h_month"]                   # ₽/ч
    labor = rate * t_all / 60
    var = dict(
        materials=sum(mat.values()),
        wire=g_wire * V["c_wire"],
        gas=gas_l / 1000 / V["v_gas"] * V["c_gas"],
        energy=kwh * V["c_kwh"],
        labor=labor,
        ins=labor * V["ins"] / 100,
    )
    AVC = sum(var.values())

    # постоянные затраты, ₽/год
    eq = V["n_posts"] * (V["c_post"] + V["c_vent"]) + V["c_stand"]
    fix = dict(
        am_eq=eq * V["am_eq"] / 100,
        am_fix=V["n_fix"] * V["c_fix"] * V["am_fix"] / 100,
        area=V["area"] * V["c_area"],
        master=V["n_m"] * V["sal_m"] * 12 * (1 + V["ins"]/100),
        other=V["other"],
    )
    FC = sum(fix.values())

    # мощность: узкое место — посты или место контроля
    fund = V["days"] * V["shifts"] * V["h_shift"] * (1 - V["k_rep"]/100) * 60      # мин/год на рабочее место
    cap_posts = V["n_posts"] * fund / t_weld_posts
    cap_ctrl = V["n_ctrl"] * fund / t_ctrl
    cap = min(cap_posts, cap_ctrl)
    N = math.floor(cap * V["load"] / 100)
    cost_full = AVC + FC / N
    price = cost_full * (1 + V["rent"] / 100)
    Qbe = FC / (price - AVC)
    return dict(ops=ops, to_sum=to_sum, L_sum=L_sum, t_weld_posts=t_weld_posts, t_all=t_all,
                masses=dict(pipe=m_pipe, bar=m_bar, sheet=m_sheet, total=sum(PARTS[k] for k in PARTS if not k.startswith("shov")) * RHO / 1000),
                mat=mat, g_wire=g_wire, gas_l=gas_l, kwh=kwh, rate=rate, var=var, AVC=AVC, fix=fix, FC=FC,
                fund=fund, cap_posts=cap_posts, cap_ctrl=cap_ctrl, cap=cap, N=N, cost_full=cost_full, price=price,
                Qbe=Qbe, Qbe_rub=Qbe * price, margin=(N - Qbe) / N, profit=N * (price - AVC) - FC,
                welders=(t_weld_posts * N / 60) / (V["h_month"] * 12 * 0.9))


if __name__ == "__main__":
    R = compute(V, WELDS, PARTS)
    print("Швы:")
    for w in WELDS:
        print("  %-28s op %s  L = %6.1f мм  V = %6.0f мм³  F = %.1f мм²" % (w["key"], w["op"], w["L"], w["V"], w["V"]/w["L"]))
    print("Σ L = %.0f мм, Σ Tо = %.2f мин" % (R["L_sum"], R["to_sum"]))
    for k, o in R["ops"].items():
        print("  %s: L %.0f мм, Tо %.2f, Tв %.2f, Tшт %.2f мин" % (k, o["L"], o["to"], o["tv"], o["tsh"]))
    print("Tшт посты %.1f мин, всего %.1f мин (%.3f н·ч)" % (R["t_weld_posts"], R["t_all"], R["t_all"]/60))
    print("Массы, кг:", {k: round(v, 3) for k, v in R["masses"].items()})
    print("Проволока %.3f кг, газ %.0f л, энергия %.3f кВт·ч, ставка %.0f ₽/ч" % (R["g_wire"], R["gas_l"], R["kwh"], R["rate"]))
    print("Переменные, ₽/шт:", {k: round(v, 1) for k, v in R["var"].items()}, "AVC =", round(R["AVC"], 1))
    print("  материалы:", {k: round(v, 1) for k, v in R["mat"].items()})
    print("Постоянные, ₽/год:", {k: round(v) for k, v in R["fix"].items()}, "FC =", round(R["FC"]))
    print("Мощность: посты %.0f, контроль %.0f → %.0f шт/год; программа N = %d" % (R["cap_posts"], R["cap_ctrl"], R["cap"], R["N"]))
    print("Полная себестоимость %.0f ₽, цена %.0f ₽" % (R["cost_full"], R["price"]))
    print("Qбу = %.0f шт (%.2f млн ₽), запас прочности %.1f%%, прибыль %.2f млн ₽, сварщиков ≈ %.1f" % (
        R["Qbe"], R["Qbe_rub"]/1e6, R["margin"]*100, R["profit"]/1e6, R["welders"]))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    out = dict(params={k: dict(v=v[0], unit=v[1], label=v[2], src=v[3]) for k, v in P.items()},
               welds=[dict(key=w["key"], op=w["op"], L=round(w["L"], 2), V=round(w["V"], 1),
                           pts=[[round(c, 2) for c in p] for p in w["pts"]]) for w in WELDS],
               parts={k: round(v, 1) for k, v in PARTS.items()},
               result={k: v for k, v in R.items()})
    with open(os.path.join(HERE, "out", "economics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=float)
    print("out/economics.json")
