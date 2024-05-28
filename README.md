<p align="center">
    <img src="./Src/Assets/min_logo.png">
</p>


This repository provide a simple script designed to facilitate the downloading of films and series from a popular streaming community platform. The script allows users to download individual films, entire series, or specific episodes, providing a seamless experience for content consumers.

## Join us
You can chat, help improve this repo, or just hang around for some fun in the **Git_StreamingCommunity** Discord [Server](https://discord.com/invite/8vV68UGRc7)

# Table of Contents

* [INSTALLATION](#installation)
  * [Requirement](#requirement)
  * [Usage](#usage)
* [CONFIGURATION](#Configuration)
* [DOCKER](#docker)
* [TUTORIAL](#tutorial)

## Requirement

Make sure you have the following prerequisites installed on your system:

* [python](https://www.python.org/downloads/) > 3.8
* [ffmpeg](https://www.gyan.dev/ffmpeg/builds/)
* [opnessl](https://www.openssl.org) or [pycryptodome](https://pypi.org/project/pycryptodome/)

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

## Configuration

You can change some behaviors by tweaking the configuration file.

<details>
  <summary><strong>DEFAULT</strong></summary>

  * **debug**: Enables or disables debug mode.
    - **Default Value**: `false`

  * **log_file**: The file where logs will be written.
    - **Default Value**: `app.log`

  * **clean_console**: Clears the console before the script runs.
    - **Default Value**: `true`

  * **root_path**: Path where the script will add movies and TV series folders (see [Path Examples](#Path-examples)).
    - **Default Value**: `Video`

  * **map_episode_name**: Mapping to choose the name of all episodes of TV Shows (see [Episode Name Usage](#Episode-name-usage)).
    - **Default Value**: `%(tv_name)_S%(season)E%(episode)_%(episode_name)`

  * **not_close**: When activated, prevents the script from closing after its initial execution, allowing it to restart automatically after completing the first run.
    - **Default Value**: `false`

</details>

<details>
  <summary><strong>M3U8_DOWNLOAD</strong></summary>

  * **tdqm_workers**: The number of workers that will cooperate to download .ts files. **A high value may slow down your PC**
    - **Default Value**: `30`

  * **tqdm_show_progress**: Whether to show progress during downloads or not.
    - **Default Value**: `true`

  * **create_report**: When enabled, saves the name of the series or movie being downloaded along with the date and file size in a CSV file, providing a log of downloaded content.
    - **Default Value**: `false`

</details>

<details>
  <summary><strong>M3U8_FILTER</strong></summary>

  * **use_codec**: Whether to use a specific codec for processing.
    - **Default Value**: `false`

  * **use_gpu**: Whether to use GPU acceleration.
    - **Default Value**: `false`

  * **default_preset**: The default preset for ffmpeg conversion.
    - **Default Value**: `ultrafast`

  * **check_output_conversion**: Verify if the conversion run by ffmpeg is free from corruption.
    - **Default Value**: `false`

  * **cleanup_tmp_folder**: Upon final conversion, ensures the removal of all unformatted audio, video tracks, and subtitles from the temporary folder, thereby maintaining cleanliness and efficiency.
    - **Default Value**: `true`

  * **specific_list_audio**: A list of specific audio languages to download.
    - **Example Value**: `['ara', 'baq', 'cat', 'chi', 'cze', 'dan', 'dut', 'eng', 'fil', 'fin', 'forced-ita', 'fre', 'ger', 'glg', 'gre', 'heb', 'hin', 'hun', 'ind', 'ita', 'jpn', 'kan', 'kor', 'mal', 'may', 'nob', 'nor', 'pol', 'por', 'rum', 'rus', 'spa', 'swe', 'tam', 'tel', 'tha', 'tur', 'ukr', 'vie']`

  * **specific_list_subtitles**: A list of specific subtitle languages to download.
    - **Example Value**: `['eng']`

</details>

<details>
  <summary><strong>M3U8_REQUESTS</strong></summary>

  * **disable_error**: Whether to disable error messages.
    - **Default Value**: `false`

  * **timeout**: The timeout value for requests.
    - **Default Value**: `10`

  * **verify_ssl**: Whether to verify SSL certificates.
    - **Default Value**: `false`

</details>

<details>
  <summary><strong>M3U8_PARSER</strong></summary>

  * **skip_empty_row_playlist**: Whether to skip empty rows in the playlist m3u8.
    - **Default Value**: `false`

  * **force_resolution**: Forces the use of a specific resolution. `-1` means no forced resolution.
    - **Default Value**: `-1`
    - **Example Value**: `1080`

</details>


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

> NOTE: You don't need to add .mp4 at the end

## Docker

You can run the script in a docker container, to build the image just run

```
docker build -t streaming-community-api .
```

and to run it use

```
docker run -it -p 8000:8000 streaming-community-api
```

By default the videos will be saved in `/app/Video` inside the container, if you want to to save them in your machine instead of the container just run

```
docker run -it -p 8000:8000 -v /path/to/download:/app/Video streaming-community-api
```

## Tutorial

For a detailed walkthrough, refer to the [video tutorial](https://www.youtube.com/watch?v=Ok7hQCgxqLg&ab_channel=Nothing)
