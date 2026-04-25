
"""
Telegram Referral Bot - FIXED: Better notification message for verified referrals
Author: Assistant
"""

import os
import json
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode

# ============ CONFIGURATION ============
BOT_TOKEN = "8703538025:AAF2cKnseYpQGGJN4k4JE2a1B30jKHK8yYg"
OWNER_IDS = [7682896710, 7765423734]
NOTIFY_GROUP_ID = -1003715248836
YOUTUBE_LINK = "https://youtube.com/yourlink"

# Files for data storage
DATA_FILE = "bot_data.json"
CHANNELS_FILE = "channels.json"
KEYS_FILE = "keys.json"
PENDING_REFERS_FILE = "pending_refers.json"

# ============ DATA MANAGEMENT ============

def load_json(filename, default=None):
    if default is None:
        default = {}
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def init_files():
    if not os.path.exists(DATA_FILE):
        save_json(DATA_FILE, {})
    if not os.path.exists(CHANNELS_FILE):
        save_json(CHANNELS_FILE, [])
    if not os.path.exists(KEYS_FILE):
        save_json(KEYS_FILE, [])
    if not os.path.exists(PENDING_REFERS_FILE):
        save_json(PENDING_REFERS_FILE, {})

def get_user_data(user_id):
    data = load_json(DATA_FILE)
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "referrals": [],
            "ref_count": 0,
            "referred_by": None,
            "keys_received": [],
            "refer_code": None,
            "verified": False
        }
        save_json(DATA_FILE, data)
    return data[user_id]

def update_user_data(user_id, key, value):
    data = load_json(DATA_FILE)
    user_id = str(user_id)
    if user_id not in data:
        get_user_data(user_id)
        data = load_json(DATA_FILE)
    data[user_id][key] = value
    save_json(DATA_FILE, data)

# ============ PENDING REFERRAL SYSTEM ============

def save_pending_refer(user_id, referrer_id):
    pending = load_json(PENDING_REFERS_FILE, {})
    user_id = str(user_id)
    pending[user_id] = str(referrer_id)
    save_json(PENDING_REFERS_FILE, pending)

def get_pending_refer(user_id):
    pending = load_json(PENDING_REFERS_FILE, {})
    return pending.get(str(user_id))

def clear_pending_refer(user_id):
    pending = load_json(PENDING_REFERS_FILE, {})
    if str(user_id) in pending:
        del pending[str(user_id)]
        save_json(PENDING_REFERS_FILE, pending)

async def process_pending_refer(user_id, context):
    """Process pending referral after user verifies channels"""
    referrer_id = get_pending_refer(user_id)
    if not referrer_id:
        return False

    data = load_json(DATA_FILE)
    user_id_str = str(user_id)

    # Check if already referred by someone
    if data[user_id_str]["referred_by"] is not None:
        clear_pending_refer(user_id)
        return False

    # Check if already in referrer's list
    if user_id_str in data[referrer_id]["referrals"]:
        clear_pending_refer(user_id)
        return False

    # Add referral
    data[referrer_id]["referrals"].append(user_id_str)
    data[referrer_id]["ref_count"] = len(data[referrer_id]["referrals"])
    data[user_id_str]["referred_by"] = referrer_id
    save_json(DATA_FILE, data)

    # Clear pending
    clear_pending_refer(user_id)

    # Get new user info for notification
    try:
        chat = await context.bot.get_chat(user_id)
        new_user_name = chat.first_name
        if chat.username:
            new_user_name = f"@{chat.username}"
    except:
        new_user_name = f"User {user_id}"

    # FIXED: Better notification message
    try:
        notify_text = (
            f"🎉 *CONGRATULATIONS! NEW REFERRAL ADDED!*\n\n"
            f"✅ A new user joined through your link and verified all channels!\n\n"
            f"👤 *New User:* {new_user_name}\n"
            f"🆔 *User ID:* `{user_id}`\n\n"
            f"📊 *Your Total Refers:* `{data[referrer_id]['ref_count']}`\n"
            f"🎯 *Remaining:* `{150 - data[referrer_id]['ref_count']}` more for FREE KEY!\n\n"
            f"⚡ Keep sharing your link to get more refers!"
        )
        await context.bot.send_message(
            int(referrer_id), 
            notify_text, 
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Failed to notify referrer {referrer_id}: {e}")

    return True

# ============ REFERRAL LINK ============

def get_refer_link(user_id, bot_username):
    return f"https://t.me/{bot_username}?start={user_id}"

# ============ CHANNEL MANAGEMENT ============

def get_channels():
    return load_json(CHANNELS_FILE, [])

def add_channel(channel_id, channel_link):
    channels = get_channels()
    for ch in channels:
        if ch["id"] == channel_id:
            return False, "Channel already exists!"
    channels.append({"id": channel_id, "link": channel_link})
    save_json(CHANNELS_FILE, channels)
    return True, "Channel added successfully!"

def remove_channel(channel_id):
    channels = get_channels()
    channels = [ch for ch in channels if ch["id"] != channel_id]
    save_json(CHANNELS_FILE, channels)
    return True, "Channel removed!"

# ============ KEY MANAGEMENT ============

def get_keys():
    return load_json(KEYS_FILE, [])

def add_key(key):
    keys = get_keys()
    if key in keys:
        return False, "Key already exists!"
    keys.append(key)
    save_json(KEYS_FILE, keys)
    return True, f"Key added! Total keys: {len(keys)}"

def remove_key(key):
    keys = get_keys()
    if key in keys:
        keys.remove(key)
        save_json(KEYS_FILE, keys)
        return True, "Key removed!"
    return False, "Key not found!"

def give_key_to_user(user_id):
    keys = get_keys()
    if not keys:
        return None, "No keys available!"
    key = keys[0]
    keys.remove(key)
    save_json(KEYS_FILE, keys)
    data = load_json(DATA_FILE)
    user_id = str(user_id)
    data[user_id]["keys_received"].append({
        "key": key,
        "date": datetime.now().isoformat(),
        "cost": 150
    })
    save_json(DATA_FILE, data)
    return key, "Success"

# ============ VERIFICATION ============

async def check_channel_status(user_id, channel_id, context):
    try:
        member = await context.bot.get_chat_member(channel_id, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True, "joined"
    except Exception:
        pass

    try:
        member = await context.bot.get_chat_member(channel_id, user_id)
        if member.status != 'left':
            return True, "pending"
    except Exception:
        pass

    return False, "not_found"

async def get_unjoined_channels(user_id, context):
    channels = get_channels()
    unjoined = []
    for ch in channels:
        is_ok, status = await check_channel_status(user_id, ch["id"], context)
        if not is_ok:
            unjoined.append(ch)
    return unjoined

# ============ KEYBOARD BUILDERS ============

def build_join_buttons(unjoined_channels, all_channels):
    keyboard = []
    for i, ch in enumerate(unjoined_channels, 1):
        keyboard.append([InlineKeyboardButton(f"JOIN {i} ✅", url=ch["link"])])
    keyboard.append([InlineKeyboardButton("✅ JOINED / REQUESTED", callback_data="verify_join")])
    return InlineKeyboardMarkup(keyboard)

def build_main_menu():
    keyboard = [
        [InlineKeyboardButton("REFER TO EARN 💰", callback_data="refer_earn")],
        [InlineKeyboardButton("GET 1 DAY KEY - 1$ 🔑", callback_data="get_key")],
        [InlineKeyboardButton("HOW TO GET KEY ❓", callback_data="how_key")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_refer_menu(refer_link):
    keyboard = [
        [InlineKeyboardButton("🔗 YOUR REFER LINK", url=refer_link)],
        [InlineKeyboardButton("📤 SHARE REFER LINK", url=f"https://t.me/share/url?url={refer_link}&text=Join%20this%20bot%20and%20earn%20free%20keys!")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    get_user_data(user_id)

    # Check for referral in start parameter
    if context.args and len(context.args) > 0:
        try:
            refer_id = str(context.args[0])
            user_id_str = str(user_id)
            data = load_json(DATA_FILE)

            # Don't count self-referral
            if refer_id != user_id_str:
                # Check if referrer exists
                if refer_id in data:
                    # Check if user already referred by someone
                    if data[user_id_str]["referred_by"] is None:
                        # Check if already in referrer's list
                        if user_id_str not in data[refer_id]["referrals"]:
                            # Save as PENDING - will process after verification
                            save_pending_refer(user_id, refer_id)
                            print(f"Pending referral saved: {user_id} -> {refer_id}")
        except Exception as e:
            print(f"Error processing referral: {e}")

    # Check channel joins
    unjoined = await get_unjoined_channels(user_id, context)

    if not unjoined:
        # All channels joined - process pending referral if any
        if get_pending_refer(user_id):
            processed = await process_pending_refer(user_id, context)
            if processed:
                await update.message.reply_text(
                    "✅ *Channels verified!*\n"
                    "🎊 *Referral counted successfully!*",
                    parse_mode=ParseMode.MARKDOWN
                )

        # Mark as verified
        update_user_data(user_id, "verified", True)
        await show_main_menu(update, context)
    else:
        channels = get_channels()
        text = "🔰 *WELCOME TO THE BOT!*\n\n"
        text += "📢 Please join all channels to use this bot:\n\n"
        text += f"⏳ Remaining: *{len(unjoined)}* channel(s)\n\n"
        text += "✅ Click the JOIN buttons and send request, then click JOINED/REQUESTED button!"

        reply_markup = build_join_buttons(unjoined, channels)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
            )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎉 *CONGRATULATIONS!*\n\n"
        "✅ You have joined all channels!\n\n"
        "💎 *IF YOU NEED DRIP CLIENT FREE KEY THEN REFER YOUR FRIEND TO GET 1$*\n\n"
        "🎯 *150 REFER = 1 DAY KEY*\n\n"
        "👇 Choose an option below:"
    )

    reply_markup = build_main_menu()

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "verify_join":
        unjoined = await get_unjoined_channels(user_id, context)
        if not unjoined:
            # All channels joined - process pending referral if any
            if get_pending_refer(user_id):
                processed = await process_pending_refer(user_id, context)
                if processed:
                    await query.answer("🎊 Referral counted!", show_alert=True)
                else:
                    await query.answer("✅ Verified!", show_alert=True)
            else:
                await query.answer("✅ Verified!", show_alert=True)

            # Mark as verified
            update_user_data(user_id, "verified", True)
            await show_main_menu(update, context)
        else:
            channels = get_channels()
            text = "❌ *You have not joined all channels yet!*\n\n"
            text += f"⏳ Remaining: *{len(unjoined)}* channel(s)\n\n"
            text += "📢 Please click JOIN buttons and send request, then click JOINED/REQUESTED!"

            reply_markup = build_join_buttons(unjoined, channels)
            await query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
            )

    elif data == "refer_earn":
        bot_username = context.bot.username
        refer_link = get_refer_link(user_id, bot_username)
        user_data = get_user_data(user_id)

        text = (
            f"💰 *REFER TO EARN*\n\n"
            f"📊 Your Total Refers: *{user_data['ref_count']}*\n\n"
            f"🎯 Target: *150 REFER = 1 DAY KEY*\n\n"
            f"🔗 *YOUR REFER LINK:*\n`{refer_link}`\n\n"
            f"📤 Share your link with friends!"
        )

        reply_markup = build_refer_menu(refer_link)
        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
        )

    elif data == "get_key":
        user_data = get_user_data(user_id)

        if user_data["ref_count"] < 150:
            remaining = 150 - user_data["ref_count"]
            text = (
                f"❌ *NOT ENOUGH REFERS!*\n\n"
                f"📊 Your Current Refers: *{user_data['ref_count']}*\n"
                f"🎯 Required: *150*\n"
                f"⏳ Remaining: *{remaining}*\n\n"
                f"⚡ *Fast complete 150 refer to get your key!*"
            )
            keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_main")]]
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
            )
        else:
            keys_list = get_keys()
            if not keys_list:
                text = (
                    "⏳ *KEYS OUT OF STOCK!*\n\n"
                    "Please wait for admin to add more keys.\n"
                    "Contact support for assistance."
                )
                keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_main")]]
                await query.edit_message_text(
                    text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
                )
                return

            key, status = give_key_to_user(user_id)
            if key:
                data = load_json(DATA_FILE)
                user_id_str = str(user_id)
                data[user_id_str]["referrals"] = data[user_id_str]["referrals"][150:]
                data[user_id_str]["ref_count"] = len(data[user_id_str]["referrals"])
                save_json(DATA_FILE, data)

                text = (
                    f"🎉 *CONGRATULATIONS!*\n\n"
                    f"✅ You have redeemed *1 DAY KEY*!\n\n"
                    f"🔑 *YOUR KEY:*\n`{key}`\n\n"
                    f"📊 Remaining Refers: *{data[user_id_str]['ref_count']}*\n\n"
                    f"💾 *Save this key!*"
                )

                # Get user info
                user = query.from_user
                user_name = user.first_name
                if user.username:
                    user_name = f"@{user.username}"

                # Send to notification group with profile photo
                try:
                    photos = await context.bot.get_user_profile_photos(user_id, limit=1)

                    caption_text = (
                        f"🎊 *NEW KEY REDEEMED!*\n\n"
                        f"👤 *Name:* {user_name}\n"
                        f"🆔 *User ID:* `{user_id}`\n"
                        f"📛 *Username:* @{user.username if user.username else 'N/A'}\n"
                        f"🔑 *Key Given:* `{key}`\n"
                        f"💰 *Cost:* 150 Refers\n"
                        f"📊 *Remaining Refers:* {data[user_id_str]['ref_count']}\n"
                        f"📅 *Date:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"[👤 View Profile](tg://user?id={user_id})"
                    )

                    if photos.total_count > 0:
                        file_id = photos.photos[0][-1].file_id
                        await context.bot.send_photo(
                            chat_id=NOTIFY_GROUP_ID,
                            photo=file_id,
                            caption=caption_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=NOTIFY_GROUP_ID,
                            text=caption_text + "\n\n📷 *Profile Photo:* Not available",
                            parse_mode=ParseMode.MARKDOWN,
                            disable_web_page_preview=True
                        )

                except Exception as e:
                    print(f"Failed to send to group: {e}")

                # Notify owners
                admin_text = (
                    f"🆕 *KEY REDEEMED!*\n\n"
                    f"👤 User: [{user_name}](tg://user?id={user_id})\n"
                    f"🆔 ID: `{user_id}`\n"
                    f"🔑 Key: `{key}`\n"
                    f"💰 Cost: 150 Refers"
                )
                for owner_id in OWNER_IDS:
                    try:
                        await context.bot.send_message(
                            owner_id, admin_text, parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception:
                        pass

                keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_main")]]
                await query.edit_message_text(
                    text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
                )
            else:
                text = f"❌ Error: {status}"
                keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_main")]]
                await query.edit_message_text(
                    text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
                )

    elif data == "how_key":
        text = (
            f"📺 *HOW TO GET KEY*\n\n"
            f"🎥 Watch the tutorial video:\n"
            f"🔗 [Click Here]({YOUTUBE_LINK})\n\n"
            f"📌 Steps:\n"
            f"1️⃣ Share your refer link\n"
            f"2️⃣ Get 150 refers\n"
            f"3️⃣ Click 'GET 1 DAY KEY'\n"
            f"4️⃣ Receive your free key!"
        )
        keyboard = [
            [InlineKeyboardButton("🎥 WATCH VIDEO", url=YOUTUBE_LINK)],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_main")]
        ]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )

    elif data == "back_main":
        await show_main_menu(update, context)

# ============ OWNER CHECK ============

async def is_owner(update: Update):
    user_id = update.effective_user.id
    return user_id in OWNER_IDS

# ============ ADMIN COMMANDS ============

async def admin_add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /add <key>")
        return

    key = " ".join(context.args)
    success, msg = add_key(key)

    if success:
        await update.message.reply_text(f"✅ Key added successfully! 🎊\n\n📊 Total keys: {len(get_keys())}")
    else:
        await update.message.reply_text(f"❌ {msg}")

async def admin_list_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return

    keys = get_keys()
    if not keys:
        await update.message.reply_text("📭 No keys available!")
        return

    text = f"🔑 *AVAILABLE KEYS ({len(keys)}):*\n\n"
    for i, key in enumerate(keys, 1):
        text += f"{i}. `{key}`\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def admin_add_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /addchannel <channel_id> <link>")
        return

    channel_id = context.args[0]
    channel_link = context.args[1]
    success, msg = add_channel(channel_id, channel_link)

    if success:
        await update.message.reply_text(f"✅ {msg}")
    else:
        await update.message.reply_text(f"❌ {msg}")

async def admin_list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return

    channels = get_channels()
    if not channels:
        await update.message.reply_text("📭 No channels configured!")
        return

    text = "📢 *CONFIGURED CHANNELS:*\n\n"
    for i, ch in enumerate(channels, 1):
        text += f"{i}. ID: `{ch['id']}`\n   Link: {ch['link']}\n\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def admin_remove_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /removechannel <channel_id>")
        return

    channel_id = context.args[0]
    success, msg = remove_channel(channel_id)

    if success:
        await update.message.reply_text(f"✅ {msg}")
    else:
        await update.message.reply_text(f"❌ {msg}")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return

    data = load_json(DATA_FILE)
    total_users = len(data)
    total_keys = len(get_keys())
    keys_given = sum(len(u.get("keys_received", [])) for u in data.values())

    text = (
        f"📊 *BOT STATISTICS*\n\n"
        f"👥 Total Users: *{total_users}*\n"
        f"🔑 Available Keys: *{total_keys}*\n"
        f"🎁 Keys Given: *{keys_given}*\n"
        f"📢 Channels: *{len(get_channels())}*"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def debug_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_owner_user = await is_owner(update)

    text = (
        f"🆔 *Your User ID:* `{user_id}`\n"
        f"👑 *Owner IDs:* {', '.join([str(x) for x in OWNER_IDS])}\n"
        f"📢 *Notify Group:* `{NOTIFY_GROUP_ID}`\n"
        f"✅ *Is Owner:* {is_owner_user}\n\n"
    )

    if is_owner_user:
        text += "👑 *You are an OWNER!*\n✅ All admin commands available!"
    else:
        text += "❌ *You are NOT an owner.*\n🚫 Admin commands disabled."

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ============ MAIN ============

def main():
    init_files()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", admin_add_key))
    application.add_handler(CommandHandler("keys", admin_list_keys))
    application.add_handler(CommandHandler("addchannel", admin_add_channel_cmd))
    application.add_handler(CommandHandler("channels", admin_list_channels))
    application.add_handler(CommandHandler("removechannel", admin_remove_channel_cmd))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("id", debug_info))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot is running...")
    print(f"👑 Owner IDs: {OWNER_IDS}")
    print(f"📢 Notify Group: {NOTIFY_GROUP_ID}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
