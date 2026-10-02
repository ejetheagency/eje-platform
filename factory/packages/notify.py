# factory/packages/notify.py
# The one alert channel for the factory. notify(subject, body) emails contact@ejetheagency.com via the
# agency Gmail SMTP (EJE_WORK creds, from env on Railway or eje-leads/.env locally). budget.forecast and
# the pool-floor rule both call this. Falls back to ntfy.sh (config NTFY_TOPIC) if no SMTP creds. NEVER
# raises: an alert failure must not break the nightly run.
import os, smtplib, urllib.request
from email.message import EmailMessage

TO = "contact@ejetheagency.com"


def _creds():
    em, pw = os.environ.get("EJE_WORK_EMAIL"), os.environ.get("EJE_WORK_APP_PW")
    if em and pw:
        return em, pw
    path = os.path.expanduser("~/claude/eje-leads/.env")
    if os.path.exists(path):
        d = {}
        for l in open(path):
            l = l.strip()
            if "=" in l and not l.startswith("#"):
                k, v = l.split("=", 1)
                d[k] = v
        return d.get("EJE_WORK_EMAIL"), d.get("EJE_WORK_APP_PW")
    return None, None


def notify(subject, body):
    try:
        em, pw = _creds()
        if em and pw:
            msg = EmailMessage()
            msg["From"] = em
            msg["To"] = TO
            msg["Subject"] = "[EJE factory] " + subject
            msg.set_content(body)
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
                s.starttls()
                s.login(em, pw)
                s.send_message(msg)
            return {"ok": True, "via": "smtp"}
        topic = os.environ.get("NTFY_TOPIC")
        if topic:
            req = urllib.request.Request("https://ntfy.sh/" + topic, data=(body or subject).encode(),
                                         headers={"Title": subject})
            urllib.request.urlopen(req, timeout=15)
            return {"ok": True, "via": "ntfy"}
        return {"ok": False, "reason": "no notify channel configured"}
    except Exception as e:
        return {"ok": False, "reason": str(e)[:150]}
