# Harmony Configuration Guide

This guide aims to document how to configure Harmony for your own use, or for development.

## Config File Documentation

This section aims to document all of the different fields in the `config.json` file, enabling you to configure the bot accordingly.

| Key                                                  | Description                                                                                                                                                                                                                                                                                                                                                                                              |
|------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `discord.bot_token`                                  | The token for your Discord bot user.                                                                                                                                                                                                                                                                                                                                                                     |
| `discord.guild_id`                                   | The ID of the server this instance of the bot resides in.                                                                                                                                                                                                                                                                                                                                                |
| `discord.harmony_management_role_id`                 | The ID of the role whose members are allowed to perform privileged operations with the bot.                                                                                                                                                                                                                                                                                                              |
| `discord.verified_role_id`                           | The ID of the role assigned to users on successful completion of the `/verify` process.                                                                                                                                                                                                                                                                                                                  |
| `reddit.client_id`                                   | The OAuth client ID of your Reddit API key.                                                                                                                                                                                                                                                                                                                                                              |
| `reddit.client_secret`                               | The OAuth client secret of your Reddit API key.                                                                                                                                                                                                                                                                                                                                                          |
| `reddit.username`                                    | The login username of the Reddit account used for servicing requests to Reddit. This account should be a moderator of the subreddit configured under `reddit.subreddit_name`.                                                                                                                                                                                                                            |
| `reddit.password`                                    | The login password of the Reddit account used for servicing requests to Reddit.                                                                                                                                                                                                                                                                                                                          |     
| `reddit.user_agent`                                  | The user agent sent in requests to Reddit. This should follow [Reddit's guidelines on user agents](https://github.com/reddit-archive/reddit/wiki/API#rules).                                                                                                                                                                                                                                             |
| `reddit.subreddit_name`                              | The subreddit to use for moderation actions.                                                                                                                                                                                                                                                                                                                                                             |
| `db.username`                                        | The username of the MongoDB user used to authenticate against the database configured in `db.db_name`.                                                                                                                                                                                                                                                                                                   |
| `db.password`                                        | The password of the MongoDB user used to authenticate against the database configured in `db.db_name`.                                                                                                                                                                                                                                                                                                   |
| `db.hostname`                                        | The hostname of the MongoDB server - this should ideally be the primary member in the set for durability reasons.                                                                                                                                                                                                                                                                                        |
| `db.port`                                            | The port on which the MongoDB server is listening.                                                                                                                                                                                                                                                                                                                                                       |
| `db.db_name`                                         | The name of the database to use.                                                                                                                                                                                                                                                                                                                                                                         |
| `db.replica_set_name`                                | The name of the replica set to use. If not present, a replica set will not be used (not recommended for production deployments!)                                                                                                                                                                                                                                                                         |
| `roles.*`                                            | A list of status roles which can be assigned by a member of the `discord.harmony_management_role_id` role. See [Roles Configuration](#roles-configuration) for information on how to configure these.                                                                                                                                                                                                    |
| `schedule.reddit_account_check_enabled`              | `true`: Check all verified members to ensure their Reddit accounts are still in good standing, as detailed in the [Reddit Account Check Job](#reddit-account-check-job) section. `false`: The check is completely disabled.                                                                                                                                                                              |
| `schedule.reddit_account_check_interval_seconds`     | How many seconds to wait before executing the [Reddit Account Check Job](#reddit-account-check-job).                                                                                                                                                                                                                                                                                                     |
| `schedule.reddit_account_check_reporting_channel_id` | The ID of the text channel to send job reports to.                                                                                                                                                                                                                                                                                                                                                       |
| `schedule.reddit_account_check_dry_run`              | If `true`, then the job will run as normal, but without taking any action (the report is generated, but no users are removed or banned and the database is not modified).                                                                                                                                                                                                                                |
| `schedule.reddit_account_check_ban_fetch_limit`      | The maximum number of bans to fetch from Reddit.                                                                                                                                                                                                                                                                                                                                                         | 
| `schedule.discord_role_check_enabled`                | `true`: Remove the verified role from all non-verified users who are a member of the `discord.verified_role_id` role, as detailed in the [Discord Verified Role Check Job](#discord-verified-role-check-job) section. This prevents moderators from subverting the verification process, and allows retroactive enforcement of applicable verification rules. `false`: The check is completely disabled. |
| `schedule.discord_role_check_interval_seconds`       | How many seconds to wait before executing the [Discord Verified Role Check Job](#discord-verified-role-check-job).                                                                                                                                                                                                                                                                                       |
| `schedule.discord_role_check_reporting_channel_id`   | The ID of the text channel to send job reports to.                                                                                                                                                                                                                                                                                                                                                       |
| `schedule.discord_role_check_dry_run`                | If `true`, then the job will run as normal, but without removing the role from any users. The report is still generated.                                                                                                                                                                                                                                                                                 |
| `ebay.http_proxy_url`                                | The URL for a HTTP proxy through which requests to eBay are sent. This is useful if you're trying to make requests to eBay's regional sites in a different country to where the instance of your bot is hosted, to avoid the bot's requests being geoblocked (e.g. if you're searching `ebay.co.uk` but your bot is hosted in Sweden).                                                                   |
| `verify.discord_minimum_account_age_days`            | The minimum age of a Discord account, in days, before the user is allowed to link their accounts.                                                                                                                                                                                                                                                                                                        | 
| `verify.reddit_minimum_account_age_days`             | The minimum age of a Reddit account, in days, before the user is allowed to link their accounts.                                                                                                                                                                                                                                                                                                         | 
| `verify.token_prefix`                                | The text that prefixes the verification token sent to the user when verifying their Reddit account.                                                                                                                                                                                                                                                                                                      | 

### Roles Configuration

To add roles for moderators to assign to users, the `roles` key in the configuration needs to have a list of one or more JSON objects, e.g.:

```json
{
  "roles": [
    {
      "role_name": "Example Trade Role",
      "discord_role_id": 0,
      "reddit_flair_text": "Hello, World!",
      "reddit_flair_css_class": "hello_world"
    },
    {...}
  ]
}
```

The fields in the JSON objects are configured as follows:

| Field name               | Description                                                                                                                                                 |
|--------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `role_name`              | The name of the role as displayed in Discord's UI, in the dropdown menu. This does not have to be the same as the role name in Discord itself.              |
| `discord_role_id`        | The ID of the role to assign when this option is selected.                                                                                                  |
| `reddit_flair_text`      | The text to set the user's Reddit flair to.                                                                                                                 |
| `reddit_flair_css_class` | The CSS class to apply to the user's Reddit flair (must be configured in Reddit beforehand). Do not include the leading dot (.) in the configuration value. |

### Scheduled Tasks

All scheduled tasks are executed immediately when the bot starts up, and re-run every `n` seconds depending on the configuration values.

> Note that Discord has strict rate limits on how many users your bot can privately message to prevent spam - enabling these jobs with a large number of users to process may cause problems in this regard.

#### Reddit Account Check Job

Every `schedule.reddit_account_check_interval_seconds` seconds, all members of the server with a verified Reddit account are checked to ensure their Reddit accounts are still in good standing.

- If their accounts are suspended from Reddit or deleted outright, their verified role (configurable under `discord.verified_role_id`) is removed and the user is notified, as well as audit trail events being sent.
- If their accounts are banned from the subreddit, the user is notified via Discord before being banned from the server.

This job will also clean up any orphaned data about a Discord member (e.g. if a member leaves the server, their verification data is deleted).

> Note that due to Reddit API's lack of an endpoint to check directly if a user is banned, a list of banned usernames up to the configured limit is fetched. This means that if a user is banned from the subreddit, but they fall outside of the returned data from Reddit (because the limit value is too small), they will not be banned from the Discord server.

Upon completion, a report of the users that have had action taken against them is sent to the channel configured under `schedule.reddit_account_check_reporting_channel_id`.

If you wish to get a sense of how many users will be impacted by the job without actually taking action, you can enable the `schedule.reddit_account_check_dry_run` flag.

#### Discord Verified Role Check Job

Every `schedule.discord_role_check_interval_seconds` seconds, all members of the server who have the `discord.verified_role_id` role but who do not have a verified Reddit account have their role removed, and are privately messaged with instructions on how to verify their account.

Upon completion, a report of the users that have had action taken against them is sent to the channel configured under `schedule.discord_role_check_reporting_channel_id`.

If you wish to get a sense of how many users will be impacted by the job without actually taking action, you can enable the `schedule.discord_role_check_dry_run` flag.

### Reddit Verification Message Template

On startup, `verification_template.md` is loaded and used to create the message sent to Redditors when they verify their account. You can write a custom template if you wish, ensuring to include the following tokens to enable the insertion of variables:

| Token                  | Description                                                                                |
|------------------------|--------------------------------------------------------------------------------------------|
| `$_username`           | The username of the Redditor who requested to verify their account, without the u/ prefix. |
| `$_guild_name`         | The name of the Discord server configured in `discord.guild_id`.                           |
| `$_verification_token` | The verification token which the user must enter to complete account verification.         |
| `$_subreddit_name`     | The name of the subreddit configured in `reddit.subreddit_name`, without the r/ prefix.    |