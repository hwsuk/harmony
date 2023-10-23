# Harmony Privacy Information

> This document is provided to you solely as a guide to help you make an informed decision about your privacy when using the Harmony Discord bot. It is not intended to act as legal advice, nor as a formal, legally-vetted privacy policy. 

In the interest of transparency, this page aims to document what information the Harmony Bot (the "Bot") collects about you in a way that is simple to understand, as well as how to request that your information be removed pursuant to any data protection or privacy laws in your relevant jurisdiction.

Note that any third party services that the bot interacts with may enforce their own privacy policies, and may collect additional data outside the scope of this bot:

- Discord
- Reddit

**No data is collected or read until you start interacting with the Bot**; the information below details the scenarios under which data would be collected and stored. 

## Age requirements

In accordance with Discord Terms of Service, all users of the Discord service must be 13 years of age or above, unless a higher age restriction is set out for the user's jurisdiction in [this support page](https://support.discord.com/hc/en-us/community/posts/360050817374-Age-restriction).

Access (the "Guild Membership") to a Discord server (the "Discord Guild") and explicit interaction with the Bot is required to collect any data. Therefore, it is not reasonably expected that the Bot will process the data of anyone too young to legally give their consent for data processing, as set out by the General Data Protection Regulation (2018) enforced in the UK, EU and EEA, and otherwise referred to as the "minimum age of digital consent".

## When verifying your account

> You may request removal of this information at any point using the `/unverify` command - no data is submitted to third parties to complete this action, and any data in the Pending Verifications database and the Verified Users database is removed with immediate effect.

When running the `/verify` slash command for the first time and entering a Reddit username, the following information is collected and saved temporarily (in memory):

- The entered Reddit username.
- Information about your Discord account.

This username is submitted to Reddit to get information about your Reddit account (to check whether it exists, whether it is in good standing, and whether it meets the account age requirements).

If your username is invalid, if you are ineligible to verify your account due to not meeting requirements, or if an error occurs at this stage, the collected information is deleted permanently.

If your Reddit username is valid and passes validation, the following information is saved to a database (the "Pending Verifications database"):

- Your Reddit username.
- Your Reddit internal account ID.
- Your Discord internal account ID.
- A list of the Discord Guild role IDs that the Bot has assigned to you (empty at this point).
- A timestamp of when you requested your account to be verified.
- A pseudo-randomised value ("the Verification Token") used to prove your ownership of the specified Reddit account

Your Reddit username is submitted to Reddit in order to send you the message containing the Verification Token.

When the verification token is entered by using `/verify`, your information is permanently deleted from the Pending Verifications database, and the following information is stored (the "Verified Users database"):

- Your Reddit username.
- Your Reddit internal account ID.
- Your Discord internal account ID.
- A list of the Discord Guild role IDs that the Bot has assigned to you (empty at this point).
- A timestamp of when you requested your account to be verified.
- A timestamp of when you completed the verification of your account.

Additionally, a temporary log (the "Debug Log") is written in order to aid diagnostics in the event of an error; this is automatically removed after 24 hours.

The collected data is used for the following purposes:

- To ensure that your Reddit account is in good standing.
- To allow other users (the "Members") of the Discord Guild to query the Verified Users database for information about a specific user (using the "Whois Command").
- During a scheduled job, if enabled, to ensure the continued good standing of your Reddit account.
- To allow moderators of the Discord Guild to perform automated actions against your Guild Membership and Reddit accounts (e.g. to update a role).

## When a moderator updates your role

When a moderator uses the Update Role functionality of the Bot in order to add a new role to your Guild Membership, the following information is retrieved from the Verified Users database:

- Your Reddit username.

This information is submitted to Reddit in order to update your user flair.

Additionally, a temporary log (the "Debug Log") is written (containing your Reddit username and Discord username) in order to aid diagnostics in the event of an error; this is automatically removed after 24 hours.

## When you encounter an error using the Bot

When an error occurs using the Bot, the following information is collected:

- A pseudo-randomised value (the "Error Reference").

A temporary log (the "Debug Log") is written (containing the Error Reference) in order to aid diagnostics in the event of an error; this is automatically removed after 24 hours.

