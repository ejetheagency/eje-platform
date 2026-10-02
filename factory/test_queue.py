# factory/test_queue.py  —  run:  python3 -m factory.test_queue
# Proves the queue + runner: enqueue -> atomic claim -> dispatch -> complete. Cleans up after itself.
from factory.packages import queue, db
from factory.workers import runner

PASS = True


def check(label, cond):
    global PASS
    print(("  PASS " if cond else "  FAIL ") + label)
    PASS = PASS and cond


def main():
    import time
    print("Queue + runner test\n")
    # a real temp company whose domain won't resolve a logo -> handler returns {ok:False} as a NORMAL dict (completes)
    co = db.insert("companies", {"dedupe_key": "TEST:q-" + str(int(time.time())),
                                 "name": "Queue Test Co", "domain": "nonexistent-xyz-12345.test"})[0]
    j = queue.enqueue("logo", company_id=co["id"])
    print("enqueued", j["id"][:8], "| queued depth:", queue.depth("queued"))
    done = runner.drain()
    print("drained:", [(d["type"], d["ok"]) for d in done])
    row = db.select("job_log", "id=eq.%s&select=status,attempt" % j["id"])[0]
    check("job was claimed + dispatched", any(d["id"] == j["id"] for d in done))
    check("job completed (status=done)", row["status"] == "done")
    check("attempt == 1 (no retries needed)", row.get("attempt") == 1)
    db.delete("job_log", "id=eq.%s" % j["id"])
    db.delete("companies", "id=eq.%s" % co["id"])
    print("\n  cleaned up")
    print("\n" + ("QUEUE TEST: PASS" if PASS else "QUEUE TEST: FAIL"))


if __name__ == "__main__":
    main()
