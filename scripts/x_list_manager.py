#!/usr/bin/env python3
"""Twitter/X List Manager - Create lists and add members.

Uses twitter-cli's authentication infrastructure (cookie extraction + curl_cffi).
Requires twitter-cli to be installed (uv tool install twitter-cli).

Usage:
    # Create a list and add members
    python x_list_manager.py create "Mobile-CE" "手机/消费电子" --members @9to5mac @MacRumors ...
    
    # Add members to existing list
    python x_list_manager.py add-members LIST_ID @handle1 @handle2 ...
    
    # List your lists
    python x_list_manager.py my-lists
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import random
import argparse

# Add twitter-cli to path so we can import its modules
TWITTER_CLI_PATH = os.path.expanduser(
    "~/.local/share/uv/tools/twitter-cli/lib/python3.13/site-packages"
)
if os.path.isdir(TWITTER_CLI_PATH):
    sys.path.insert(0, TWITTER_CLI_PATH)

from twitter_cli.auth import get_cookies
from twitter_cli.client import TwitterClient, _url_fetch
from twitter_cli.graphql import (
    FEATURES,
    _resolve_query_id,
    _cached_query_ids,
)

# Inject List-related queryIds that twitter-cli doesn't have
_LIST_QUERY_IDS = {
    "CreateList": "UQRa0jJ9doxGEIQRea1Y0w",
    "DeleteList": "UnN9Th1BDbeLjpgjGSpL3Q",
    "UpdateList": "zotgs3U-FVUY87mygvnsNQ",
    "ListAddMember": "vWPi0CTMoPFsjsL6W4IynQ",
    "ListRemoveMember": "cAGvZIu7SW0YlLYynz3VYA",
    "ListMembers": "oZLcyjKOfXBf2Jln31YXPw",
    "ListOwnerships": "BBLgNbbUu6HXAX11lV_1Qw",
    "ListSubscribe": "Gpws7iVbAR7ebO3qCCYmPw",
    "ListUnsubscribe": "-diULb6PX5grQ_MvItGiJQ",
    "ListsManagementPageTimeline": "l-5QEeuPoi2qPdDmWPKPyA",
    "CombinedLists": "ZXzJIm2PV7zaBnSF2BTBYQ",
}
_cached_query_ids.update(_LIST_QUERY_IDS)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_client() -> TwitterClient:
    """Build an authenticated TwitterClient."""
    cookies = get_cookies()
    return TwitterClient(
        auth_token=cookies["auth_token"],
        ct0=cookies["ct0"],
        cookie_string=cookies.get("cookie_string"),
    )


def create_list(client: TwitterClient, name: str, description: str = "", is_private: bool = False) -> dict:
    """Create a new Twitter List.
    
    Returns dict with list info including id_str.
    """
    variables = {
        "isPrivate": is_private,
        "name": name,
        "description": description,
    }
    
    data = client._graphql_post("CreateList", variables)
    
    list_result = data.get("data", {}).get("list", {})
    if not list_result:
        # Try alternative response paths
        list_result = data.get("data", {}).get("create_list", {})
    
    list_id = list_result.get("id_str", "") or list_result.get("id", "")
    list_name = list_result.get("name", name)
    
    if list_id:
        logger.info("✅ Created list '%s' (ID: %s)", list_name, list_id)
    else:
        logger.warning("⚠️  List creation response: %s", json.dumps(data, indent=2)[:500])
        # Try to extract from nested structure
        for key, val in data.get("data", {}).items():
            if isinstance(val, dict):
                if "id_str" in val:
                    list_id = val["id_str"]
                    break
                if "list" in val and isinstance(val["list"], dict):
                    list_id = val["list"].get("id_str", "")
                    break
    
    return {"id": list_id, "name": list_name, "data": data}


def add_member_to_list(client: TwitterClient, list_id: str, user_id: str) -> bool:
    """Add a user to a Twitter List by user ID."""
    variables = {
        "listId": list_id,
        "userId": user_id,
    }
    
    try:
        data = client._graphql_post("ListAddMember", variables)
        # Check for errors
        if isinstance(data, dict) and data.get("errors"):
            err = data["errors"][0].get("message", "Unknown error")
            logger.warning("  ⚠️  API error: %s", err)
            return False
        return True
    except Exception as e:
        logger.warning("  ❌ Failed to add user %s: %s", user_id, e)
        return False


def resolve_and_add(client: TwitterClient, list_id: str, screen_name: str) -> bool:
    """Resolve screen_name to user_id and add to list."""
    sn = screen_name.lstrip("@")
    try:
        user_id = client.resolve_user_id(sn)
        logger.info("  Resolved @%s → %s", sn, user_id)
    except Exception as e:
        logger.warning("  ❌ Cannot resolve @%s: %s", sn, e)
        return False
    
    success = add_member_to_list(client, list_id, user_id)
    if success:
        logger.info("  ✅ Added @%s to list %s", sn, list_id)
    
    # Rate limit delay
    time.sleep(random.uniform(1.5, 3.0))
    return success


def get_my_lists(client: TwitterClient) -> list:
    """Fetch the authenticated user's lists."""
    # Use REST API endpoint for owned lists
    try:
        me = client.fetch_me()
        user_id = me.id
    except Exception as e:
        logger.error("Failed to fetch current user: %s", e)
        return []
    
    # Try GraphQL endpoint for user's lists
    variables = {
        "userId": user_id,
        "count": 100,
    }
    
    try:
        data = client._graphql_get("ListsManagementPageTimeline", variables, FEATURES)
        instructions = data.get("data", {}).get("user", {}).get("result", {}).get("lists_timeline", {}).get("timeline", {}).get("instructions", [])
        
        lists = []
        for inst in instructions:
            entries = inst.get("entries", [])
            for entry in entries:
                content = entry.get("content", {})
                item_content = content.get("itemContent", {})
                list_data = item_content.get("list", {})
                if list_data:
                    lists.append({
                        "id": list_data.get("id_str", ""),
                        "name": list_data.get("name", ""),
                        "description": list_data.get("description", ""),
                        "member_count": list_data.get("member_count", 0),
                        "mode": list_data.get("mode", ""),
                    })
        return lists
    except Exception as e:
        logger.warning("GraphQL lists failed (%s), trying REST API", e)
    
    # Fallback: REST API
    try:
        url = f"https://x.com/i/api/1.1/lists/ownerships.json?user_id={user_id}&count=100"
        data = client._api_get(url)
        lists = []
        for lst in data.get("lists", []):
            lists.append({
                "id": lst.get("id_str", ""),
                "name": lst.get("name", ""),
                "description": lst.get("description", ""),
                "member_count": lst.get("member_count", 0),
                "mode": lst.get("mode", ""),
            })
        return lists
    except Exception as e:
        logger.error("REST API lists also failed: %s", e)
        return []


# ── Predefined list configurations ────────────────────────────────────

LISTS = {
    "mobile": {
        "name": "Mobile-CE",
        "description": "手机厂商、手机爆料、消费电子媒体",
        "members": [
            "9to5mac", "appleinsider", "CentroLeaks", "creativestrat",
            "encoword", "Huawei", "HuaweiMobile", "KenHu_Huawei",
            "MacRumors", "mweinbach", "nakajimegame", "OnLeaks",
            "oppo", "OPPOMobileKL", "ShishirShelke1", "tim_cook",
            "UniverseIce", "WindowsLatest", "yabhishekhd",
        ],
    },
    "general": {
        "name": "General-Tech",
        "description": "科技媒体、VC/投资人、新闻、财经、综合",
        "members": [
            "_reachsumit", "Abmankendrick", "AppStore", "baicai003",
            "BBCBreaking", "BBCWorld", "BTCdayu", "business",
            "BuzzFeed", "Cartidise", "CasualEffects", "CEOBriefing",
            "ChineseWSJ", "CNBCtech", "cnfinancewatch", "DavidSacks",
            "DeFiTeddy2020", "engadget", "foxshuo", "ftworldnews",
            "FuSheng_0306", "fxtrader", "garrytan", "Gm_t18",
            "HanyangWang", "hooeem", "JasmineJaksic", "jukan05",
            "koreatimescokr", "lennysan", "Linmiv", "Love1mothe",
            "nake13", "natfriedman", "NewsCaixin", "nikitabier",
            "panda_liyin", "paulg", "PiQSuite", "poezhao0605",
            "Polymarket", "QQ_Timmy", "reidhoffman", "Reuters",
            "ReutersBiz", "SawyerMerritt", "Similarweb",
            "StockSavvyShay", "TechCrunch", "techeconomyana",
            "Techmeme", "thedankoe", "TweakTown", "UW",
            "verge", "vista8", "vkhosla", "WSJ",
            "ycombinator", "yiguxia", "yq_acc", "yuyy614893671",
            "zaobaosg",
        ],
    },
}


def main():
    parser = argparse.ArgumentParser(description="Twitter/X List Manager")
    sub = parser.add_subparsers(dest="command")
    
    # create command
    p_create = sub.add_parser("create", help="Create a list and optionally add members")
    p_create.add_argument("list_key", choices=list(LISTS.keys()) + ["custom"],
                          help="Predefined list key or 'custom'")
    p_create.add_argument("--name", help="Custom list name")
    p_create.add_argument("--description", default="", help="List description")
    p_create.add_argument("--private", action="store_true", help="Create as private list")
    p_create.add_argument("--members", nargs="*", help="Screen names to add")
    p_create.add_argument("--skip-existing", action="store_true",
                          help="Skip if list with same name exists")
    
    # add-members command
    p_add = sub.add_parser("add-members", help="Add members to existing list")
    p_add.add_argument("list_id", help="List ID")
    p_add.add_argument("members", nargs="+", help="Screen names to add")
    
    # my-lists command
    sub.add_parser("my-lists", help="Show your lists")
    
    # create-all command  
    sub.add_parser("create-all", help="Create all predefined lists (mobile + general)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    logger.info("🔐 Authenticating...")
    client = build_client()
    logger.info("✅ Authenticated")
    
    if args.command == "my-lists":
        lists = get_my_lists(client)
        if not lists:
            print("No lists found (or API returned empty)")
            return
        print(f"\n📋 Your lists ({len(lists)}):\n")
        for lst in lists:
            mode = "🔒" if lst.get("mode") == "Private" else "🌐"
            print(f"  {mode} {lst['name']} (ID: {lst['id']}) - {lst['member_count']} members")
            if lst.get("description"):
                print(f"     {lst['description']}")
        print()
        return
    
    if args.command == "create":
        if args.list_key == "custom":
            name = args.name or "My List"
            desc = args.description
            members = [m.lstrip("@") for m in (args.members or [])]
        else:
            cfg = LISTS[args.list_key]
            name = args.name or cfg["name"]
            desc = args.description or cfg["description"]
            members = cfg["members"]
        
        result = create_list(client, name, desc, args.private)
        list_id = result["id"]
        
        if not list_id:
            logger.error("❌ Failed to create list")
            return
        
        if members:
            logger.info("Adding %d members to '%s' (ID: %s)...", len(members), name, list_id)
            success = 0
            failed = []
            for sn in members:
                if resolve_and_add(client, list_id, sn):
                    success += 1
                else:
                    failed.append(sn)
            
            logger.info("\n📊 Results: %d/%d added successfully", success, len(members))
            if failed:
                logger.info("❌ Failed: %s", ", ".join(f"@{f}" for f in failed))
    
    elif args.command == "add-members":
        list_id = args.list_id
        members = [m.lstrip("@") for m in args.members]
        
        logger.info("Adding %d members to list %s...", len(members), list_id)
        success = 0
        failed = []
        for sn in members:
            if resolve_and_add(client, list_id, sn):
                success += 1
            else:
                failed.append(sn)
        
        logger.info("\n📊 Results: %d/%d added successfully", success, len(members))
        if failed:
            logger.info("❌ Failed: %s", ", ".join(f"@{f}" for f in failed))
    
    elif args.command == "create-all":
        for key, cfg in LISTS.items():
            logger.info("\n{'='*50}")
            logger.info("Creating list: %s", cfg["name"])
            logger.info("{'='*50}")
            
            result = create_list(client, cfg["name"], cfg["description"])
            list_id = result["id"]
            
            if not list_id:
                logger.error("❌ Failed to create '%s', skipping", cfg["name"])
                continue
            
            logger.info("Adding %d members...", len(cfg["members"]))
            success = 0
            failed = []
            for sn in cfg["members"]:
                if resolve_and_add(client, list_id, sn):
                    success += 1
                else:
                    failed.append(sn)
            
            logger.info("📊 '%s': %d/%d added", cfg["name"], success, len(cfg["members"]))
            if failed:
                logger.info("❌ Failed: %s", ", ".join(f"@{f}" for f in failed))
            
            # Pause between lists
            time.sleep(5)


if __name__ == "__main__":
    main()
