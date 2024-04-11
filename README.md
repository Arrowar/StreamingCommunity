<p align="center" >
  <img src="./Src/Assets/min_logo.png" title="SDWebImage logo" float=left>
</p>

# Overview.

This repository provide a simple script designed to facilitate the downloading of films and series from a popular streaming community platform. The script allows users to download individual films, entire series, or specific episodes, providing a seamless experience for content consumers.

## Join us
You can chat, help improve this repo, or just hang around for some fun in the **Git_StreamingCommunity** Discord [Server](https://discord.gg/we8n4tfxFs)
# Table of Contents

* [INSTALLATION](#installation)

  * [Requirement](#requirement)
  * [Usage](#usage)
  * [Update](#update)
* [USAGE AND OPTIONS](#options)
* [TUTORIAL](#tutorial)

## Requirement

Make sure you have the following prerequisites installed on your system:

* python > [3.11](https://www.python.org/downloads/)
* ffmpeg [win](https://www.gyan.dev/ffmpeg/builds/)

## Installation

Install the required Python libraries using the following command:

```
pip install -r requirements.txt
```

## Usage

Run the script with the following command:

#### On Windows:

```powershell
python run.py
```

#### On Linux/MacOS:

```bash
python3 run.py
```

## Update

Keep your script up to date with the latest features by running:

#### On Windows:

```powershell
python update.py
```

#### On Linux/MacOS:

```bash
python3 update.py
```

## Configuration

You can change some behaviors by tweaking the configuration file.


#### Options

| Key                        | Default Value | Description                                                                                                                 | Value Example            |
| -------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| DEFAULT                    |               | Contains default configuration options for users.                                                                           |                          |
| debug                      | false         | Whether debugging information should be displayed or not.                                                                   | true                     |
| get_info                   | false         | Whether additional information should be fetched or not with debug enable.                                                  | true                     |
| show_message               | true          | Whether messages should be displayed to the user or not.                                                                    | false                    |
| clean_console              | true          | Whether the console should be cleared before displaying new information or not.                                             | false                    |
| get_moment_title           | false         | Whether to fetch the title of the moment or not.                                                                            | true                     |
| root_path                  | videos        | Path where the script will add movies and TV series folders (see[Path Examples](#Path-examples)).                           | media/streamingcommunity |
| movies_folder_name         | Movies        | The folder name where all the movies will be placed. Do not put a trailing slash.                                           | downloaded-movies        |
| series_folder_name         | Series        | The folder name where all the TV series will be placed. Do not put a trailing slash.                                        | mytvseries               |
| anime_folder_name          | Anime         | The folder name where all the anime will be placed. Do not put a trailing slash.                                            | myanime                  |
| not_close                  | false         | Whether to keep the application running after completion or not.                                                            | true                     |
| -------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| SITE                       |               | Contains site-specific configuration options.                                                                               |                          |
| streaming_domain           | forum         | The domain of the streaming site.                                                                                           | express                  |
| anime_domain               | to            | The domain of the anime site.                                                                                               | estate                   |
| -------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| M3U8                       |               | Contains options specific to M3U8.                                                                                          |                          |
| tdqm_workers               | 20            | The number of workers that will cooperate to download .ts files.**A high value may slow down your PC**                      | 40                       |
| tqdm_progress_timeout      | 10            | The timeout duration for progress display updates in seconds after quit download.                                           | 5                        |
| minimum_ts_files_in_folder | 15            | The minimum number of .ts files expected in a folder.                                                                       | 10                       |
| download_percentage        | 1             | The percentage of download completion required to consider the download complete.                                           | 0.95                     |
| requests_timeout           | 5             | The timeout duration for HTTP requests in seconds.                                                                          | 10                       |
| use_openssl                | false          | Indicates whether OpenSSL should be utilized for encryption during the conversion of TS files with key and IV.             | true                     |
| use_codecs                 | false          | Specifies whether specific codecs (e.g., h264 for video, AAC for audio) should be used for converting TS files to MP4.      | true                     |
| enable_time_quit           | false         | Whether to enable quitting the download after a certain time period.                                                        | true                     |
| tqdm_show_progress         | false         | Whether to show progress during downloads or not.**May slow down your PC**                                                  | true                     |
| cleanup_tmp_folder         | true          | Whether to clean up temporary folders after processing or not.                                                              | false                    |
| -------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| M3U8_OPTIONS               |               | Contains options specific to M3U8 file format.                                                                              |                          |
| download_audio             | true          | Indicates whether audio files should be downloaded or not.                                                                  | false                    |
| download_subtitles         | true          | Indicates whether subtitles should be downloaded or not.                                                                    | false                    |
| merge_subtitles         | true          | Indicates if you want to merge subs in mp4 file or separate files .vtt| false                    |
| specific_list_audio        | ["ita"]       | A list of specific audio languages to download.                                                                             | ["eng", "fra"]           |
| specific_list_subtitles    | ["eng"]       | A list of specific subtitle languages to download.                                                                          | ["spa", "por"]           |
|map_episode_name   |%(tv_name)_S%(season)E%(episode)_%(episode_name)| Mapping to choose the name of all episode of TV Show (see [Episode Name Usage](#Episode-name-usage)).

> [!IMPORTANT]
> If you're on **Windows** you'll need to use double black slashes. On Linux/MacOS, one slash is fine.

#### Path examples:

* Windows: `C:\\MyLibrary\\Folder` or `\\\\MyServer\\MyLibrary` (if you want to use a network folder).
* Linux/MacOS: `Desktop/MyLibrary/Folder`

#### Episode name usage:
You can choose different vars:
* `%(tv_name)` : Is the name of TV Show
* `%(season)` : Is the number of the season
* `%(episode)` : Is the number of the episode
* `%(episode_name)` : Is the name of the episode
>NOTE: You don't need to add .mp4 at the end

## Tutorial
For a detailed walkthrough, refer to the [video tutorial](https://www.youtube.com/watch?v=Ok7hQCgxqLg&ab_channel=Nothing)
