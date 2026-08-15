"""USTA — Streamlit arayüzü.

    .venv/bin/streamlit run app.py

TASARIM NOTLARI
---------------
Palet endüstriyel slate + semantik arıza renkleri. Fault/alarm ayrımı yalnızca
renkle değil METİNLE de veriliyor (WCAG color-not-only): renk körü bir teknisyen
"sürücü durur" ile "çalışmaya devam eder" arasındaki farkı kaçırmamalı.

Google Fonts KULLANILMIYOR. Ürünün tek vaadi çevrimdışı çalışmak; CDN'den font
çekmek hem bu vaadi bozar hem de internetsiz ortamda sayfayı bozar. Sistem font
yığını kullanılıyor — hata kodları için monospace, gövde için sistem sans.
"""

from __future__ import annotations

import time

import streamlit as st

import config
from src import assistant, output

st.set_page_config(
    page_title="USTA — Saha Asistanı",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
  :root {
    --u-bg:        #F8FAFC;
    --u-surface:   #FFFFFF;
    --u-ink:       #0F172A;
    --u-ink-2:     #475569;
    --u-ink-3:     #64748B;
    --u-border:    #E2E8F0;
    --u-primary:   #334155;
    --u-fault:     #DC2626;
    --u-fault-bg:  #FEF2F2;
    --u-alarm:     #B45309;
    --u-alarm-bg:  #FFFBEB;
    --u-ok:        #059669;
    --u-ok-bg:     #ECFDF5;
    --u-mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --u-bg:       #0F1518;
      --u-surface:  #182025;
      --u-ink:      #E2E8F0;
      --u-ink-2:    #94A3B8;
      --u-ink-3:    #64748B;
      --u-border:   #2A353C;
      --u-primary:  #94A3B8;
      --u-fault:    #F87171;
      --u-fault-bg: #2A1618;
      --u-alarm:    #FBBF24;
      --u-alarm-bg: #2A2110;
      --u-ok:       #34D399;
      --u-ok-bg:    #0F2A20;
    }
  }

  /* Streamlit varsayılan üst boşluğunu kıs — yoğunluk 8 */
  .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 68rem; }
  #MainMenu, footer { visibility: hidden; }

  .u-head {
    display: flex; align-items: baseline; gap: .9rem; flex-wrap: wrap;
    border-bottom: 2px solid var(--u-ink); padding-bottom: .7rem; margin-bottom: .3rem;
  }
  .u-name {
    font-family: var(--u-mono); font-size: 1.6rem; font-weight: 700;
    letter-spacing: .04em; color: var(--u-ink);
  }
  .u-sub { color: var(--u-ink-3); font-size: .82rem; }

  .u-status {
    display: inline-flex; align-items: center; gap: .4rem;
    font-family: var(--u-mono); font-size: .7rem; letter-spacing: .06em;
    padding: .2rem .55rem; border-radius: 3px;
    background: var(--u-ok-bg); color: var(--u-ok);
    border: 1px solid var(--u-ok);
  }
  .u-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--u-ok); }

  /* Aciliyet rozeti — renk TEK BAŞINA anlam taşımıyor, metin de var */
  .u-sev {
    display: inline-block; font-family: var(--u-mono); font-size: .72rem;
    font-weight: 600; letter-spacing: .04em; padding: .22rem .6rem;
    border-radius: 3px; border-left: 3px solid;
  }
  .u-sev.fault { background: var(--u-fault-bg); color: var(--u-fault); border-color: var(--u-fault); }
  .u-sev.alarm { background: var(--u-alarm-bg); color: var(--u-alarm); border-color: var(--u-alarm); }
  .u-sev.both  { background: var(--u-alarm-bg); color: var(--u-alarm); border-color: var(--u-alarm); }

  .u-src {
    font-family: var(--u-mono); font-size: .74rem; color: var(--u-ink-2);
    padding: .35rem 0; border-bottom: 1px solid var(--u-border);
    display: flex; justify-content: space-between; gap: 1rem;
  }
  .u-src:last-child { border-bottom: 0; }
  .u-src .code { color: var(--u-fault); font-weight: 600; }

  .u-meta {
    font-family: var(--u-mono); font-size: .7rem; color: var(--u-ink-3);
    letter-spacing: .03em; margin-top: .8rem;
  }
  .u-meta .k { color: var(--u-ok); }

  .u-warn {
    background: var(--u-alarm-bg); border-left: 3px solid var(--u-alarm);
    padding: .7rem .9rem; font-size: .82rem; color: var(--u-ink-2);
    margin-top: 1rem;
  }
  .u-warn strong { color: var(--u-alarm); }

  .u-empty {
    border: 1px dashed var(--u-border); padding: 1.6rem; text-align: center;
    color: var(--u-ink-3); font-size: .9rem;
  }
  .u-kv { font-family: var(--u-mono); font-size: .74rem; color: var(--u-ink-2);
          display: flex; justify-content: space-between; padding: .2rem 0; }
  .u-kv b { color: var(--u-ink); font-variant-numeric: tabular-nums; }

  .stTextInput input { font-size: 1rem; }
  .stTextInput input:focus { outline: 2px solid var(--u-primary); outline-offset: 1px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

SEVERITY = {
    "fault": ("FAULT", "sürücü durur"),
    "alarm": ("ALARM", "çalışmaya devam eder"),
    "both": ("WARNING / ALARM", "yapılandırmaya bağlı"),
}

ORNEKLER = [
    "F30002 ne demek",
    "soğutma fanı çalışmıyor",
    "fren direnci arızalı",
    "şebekede faz kaybı var",
]


@st.cache_resource(show_spinner="Modeller yükleniyor — ilk açılışta biraz sürer...")
def kur():
    usta = assistant.kur()
    istatistik = {
        r["vendor"]: r["n"] for r in usta.conn.execute(
            "SELECT d.vendor, count(*) n FROM chunks c "
            "JOIN documents d ON d.id = c.doc_id GROUP BY d.vendor")
    }
    return usta, istatistik


def kaynak_satiri(s) -> str:
    kod = f'<span class="code">{s.fault_code}</span>' if s.fault_code else ""
    return f'<div class="u-src"><span>{kod} {s.kaynak()}</span></div>'


def main() -> None:
    usta, istatistik = kur()
    toplam = sum(istatistik.values())

    st.markdown(
        '<div class="u-head">'
        '<span class="u-name">USTA</span>'
        '<span class="u-sub">Universal Servis &amp; Teknik Asistan</span>'
        '<span style="flex:1"></span>'
        '<span class="u-status"><span class="u-dot"></span>ÇEVRİMDIŞI · AĞ İSTEĞİ 0</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("**Bilgi tabanı**")
        for marka, n in sorted(istatistik.items()):
            st.markdown(f'<div class="u-kv"><span>{marka}</span><b>{n}</b></div>',
                        unsafe_allow_html=True)
        st.markdown(f'<div class="u-kv" style="border-top:1px solid var(--u-border);'
                    f'margin-top:.3rem;padding-top:.3rem"><span>toplam</span>'
                    f'<b>{toplam}</b></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Modeller**")
        st.markdown(
            f'<div class="u-kv"><span>sohbet</span><b>{config.CHAT_MODEL}</b></div>'
            f'<div class="u-kv"><span>embedding</span><b>{config.EMBEDDING_MODEL}</b></div>',
            unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(
            '<div class="u-warn"><strong>⚠ Güvenlik</strong><br>'
            'Bu araç doküman arama aracıdır, servis prosedürünün yerine geçmez. '
            'DC bara kondansatörleri güç kesildikten sonra dakikalarca yüksek '
            'gerilim tutar. Enerjili ekipmanda <strong>LOTO</strong> uygulayın.'
            '</div>', unsafe_allow_html=True)

    soru = st.text_input(
        "Arıza kodu veya belirti",
        placeholder="Örn: F30002 ne demek  ·  soğutma fanı çalışmıyor",
        help="Hata kodu yazarsan doğrudan manuel girdisi gelir (anında). "
             "Belirti tarif edersen semantik arama yapılır.",
    )

    secili = None
    kolonlar = st.columns(len(ORNEKLER))
    for kolon, ornek in zip(kolonlar, ORNEKLER):
        if kolon.button(ornek, use_container_width=True):
            secili = ornek
    soru = secili or soru

    if not soru:
        st.markdown(
            '<div class="u-empty">Bir hata kodu veya belirti girin.<br>'
            f'{toplam} arıza kaydı · Siemens · ABB · Danfoss</div>',
            unsafe_allow_html=True)
        return

    t0 = time.perf_counter()
    with st.spinner("Aranıyor..."):
        arama, satirlar = usta.akisli(soru, aciliyet_satiri=False)
    t_arama = time.perf_counter() - t0

    if arama.cevrildi:
        st.caption(f'Arama: "{arama.arama_sorgusu}"')

    # Reddedilen sorguda retrieval yine sonuç döndürür (eşiğin ALTINDA oldukları
    # için reddedilmiştir). Bunları göstermek yanıltıcı olur: "bilmiyorum" derken
    # aciliyet rozeti ve kaynak listelemek, cevap verdiğimiz izlenimi yaratır.
    cevap_var = arama.alakali_mi()

    if cevap_var and arama.sonuclar and arama.sonuclar[0].severity in SEVERITY:
        etiket, aciklama = SEVERITY[arama.sonuclar[0].severity]
        st.markdown(
            f'<span class="u-sev {arama.sonuclar[0].severity}">{etiket}</span>'
            f'<span class="u-sub"> — {aciklama}</span>',
            unsafe_allow_html=True)

    # Akışlı cevap: satırlar geldikçe yaz
    yer = st.empty()
    birikmis: list[str] = []
    ilk = None
    for satir in satirlar:
        if ilk is None:
            ilk = time.perf_counter() - t0
        birikmis.append(satir)
        yer.markdown("\n".join(birikmis))
    toplam_sure = time.perf_counter() - t0

    if cevap_var and arama.sonuclar:
        st.markdown("**Kaynaklar**")
        st.markdown("".join(kaynak_satiri(s) for s in arama.sonuclar),
                    unsafe_allow_html=True)

    if not cevap_var:
        yol_etiketi = "eşiğin altında — model çağrılmadı"
    elif arama.yol == "exact":
        yol_etiketi = "indeksli eşleşme — model çağrılmadı"
    else:
        yol_etiketi = "hibrit arama"
    st.markdown(
        f'<div class="u-meta">yol <span class="k">{yol_etiketi}</span> · '
        f'arama {t_arama:.1f} sn · ilk satır {ilk or 0:.1f} sn · '
        f'toplam {toplam_sure:.1f} sn · ağ isteği <span class="k">0</span></div>',
        unsafe_allow_html=True)


if __name__ == "__main__":
    main()
