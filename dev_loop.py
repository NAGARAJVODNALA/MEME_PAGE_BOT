import sys
import json
import time
import pathlib
import subprocess

WORKFLOW_FILE = "post_meme.yml"
POSTS_DIR = pathlib.Path("posts/wearechillclub")


def run(cmd, check=True):
    res = subprocess.run(cmd, text=True, capture_output=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}):\n{res.stderr or res.stdout}")
    return res


def commit_and_trigger(message):
    run(["git", "add", "-A"])
    status = run(["git", "status", "--porcelain"]).stdout.strip()
    if status:
        run(["git", "commit", "-m", message])
        run(["git", "pull", "--rebase", "origin", "main"])
        run(["git", "push"])
        print("Committed and pushed local changes to main.")
    else:
        print("No local changes to commit; triggering workflow directly.")

    run(["gh", "workflow", "run", WORKFLOW_FILE, "--ref", "main"])
    time.sleep(3)

    runs_json = run([
        "gh", "run", "list", "--workflow", WORKFLOW_FILE, "--limit", "1",
        "--json", "databaseId,status,conclusion,url"
    ]).stdout
    latest = json.loads(runs_json)[0]
    run_id = str(latest["databaseId"])
    print(f"Triggered run #{run_id}: {latest['url']}")

    watch = subprocess.run(["gh", "run", "watch", run_id, "--exit-status"])
    logs = run(["gh", "run", "view", run_id, "--log"], check=False).stdout
    log_tail = "\n".join(logs.splitlines()[-80:])
    print("\n--- Run Log Tail ---")
    print(log_tail)

    run(["git", "pull", "--rebase", "origin", "main"], check=False)
    inspect_latest_post()
    if watch.returncode != 0:
        print("\nWorkflow reported a failure. Share the log tail above to rewrite.")


def inspect_latest_post():
    if not POSTS_DIR.exists():
        print("\nNo posts/wearechillclub directory pulled yet.")
        return
    stories = sorted(POSTS_DIR.glob("story_*.json"))
    reels = sorted(POSTS_DIR.glob("reel_*.mp4"))
    print("\n--- Latest Generated Output in Git ---")
    print(f"Latest story JSON: {stories[-1] if stories else 'none'}")
    print(f"Latest reel MP4:   {reels[-1] if reels else 'none'}")
    if stories:
        data = json.loads(stories[-1].read_text(encoding="utf-8"))
        print(f"Hook: {data.get('top_hook')}")
        print(f"Concept: {data.get('story_concept')}")
        print(f"IG Caption: {data.get('ig_caption')}")


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]).strip() or "Update meme_agent pipeline"
    commit_and_trigger(msg)
