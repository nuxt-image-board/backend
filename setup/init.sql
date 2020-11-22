SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

CREATE TABLE `data_comment` (
  `commentID` int(11) NOT NULL,
  `commentBody` varchar(500) NOT NULL,
  `commentCreated` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `commentUpdated` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `illustID` int(11) NOT NULL,
  `userID` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_illust` (
  `illustID` int(11) NOT NULL,
  `userID` int(11) DEFAULT NULL,
  `artistID` int(11) DEFAULT NULL,
  `illustName` varchar(50) DEFAULT NULL,
  `illustDescription` varchar(200) DEFAULT NULL,
  `illustDate` datetime DEFAULT CURRENT_TIMESTAMP,
  `illustPage` tinyint(2) DEFAULT NULL,
  `illustLike` int(11) DEFAULT '0',
  `illustView` int(11) NOT NULL DEFAULT '0',
  `illustOriginUrl` varchar(100) DEFAULT NULL,
  `illustOriginSite` varchar(20) DEFAULT NULL,
  `illustNsfw` tinyint(1) DEFAULT '0',
  `illustHash` bigint(20) UNSIGNED DEFAULT NULL,
  `illustExtension` varchar(5) NOT NULL DEFAULT 'png',
  `illustWidth` smallint(6) NOT NULL DEFAULT '0',
  `illustHeight` smallint(6) NOT NULL DEFAULT '0',
  `illustStatus` tinyint(4) NOT NULL DEFAULT '0' COMMENT '	0=通常,1=検索にヒットしない,2=404',
  `illustBytes` int(11) NOT NULL DEFAULT '0',
  `illustStarYellow` int(11) NOT NULL DEFAULT '0',
  `illustStarGreen` int(11) NOT NULL DEFAULT '0',
  `illustStarRed` int(11) NOT NULL DEFAULT '0',
  `illustStarBlue` int(11) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_invite` (
  `inviteID` int(11) NOT NULL,
  `inviter` int(11) DEFAULT NULL,
  `invitee` int(11) DEFAULT NULL,
  `inviteCode` varchar(10) DEFAULT NULL,
  `inviteCreated` datetime DEFAULT CURRENT_TIMESTAMP,
  `inviteUsed` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_log` (
  `logID` int(11) NOT NULL,
  `userID` int(11) DEFAULT NULL,
  `logType` int(11) DEFAULT NULL,
  `logDate` datetime DEFAULT NULL,
  `logMessage` varchar(300) DEFAULT NULL,
  `logParam1` tinyint(4) DEFAULT '0',
  `logParam2` tinyint(4) DEFAULT '0',
  `logParam3` tinyint(4) DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_mute` (
  `muteID` int(11) NOT NULL,
  `userID` int(11) NOT NULL,
  `targetType` int(11) NOT NULL COMMENT '0=未使用, 1=タグ(キャラ含む), 2=絵師',
  `targetID` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_mylist` (
  `mylistID` int(11) NOT NULL,
  `illustID` int(11) NOT NULL,
  `mylistAddedDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_news` (
  `newsID` int(11) NOT NULL,
  `newsDate` datetime DEFAULT CURRENT_TIMESTAMP,
  `newsColor` tinyint(4) DEFAULT '0' COMMENT '0=お知らせ 1=メモ 2=アプデ 3=告知 4=重要',
  `newsTitle` varchar(50) DEFAULT NULL,
  `newsBody` varchar(300) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_notify` (
  `notifyID` int(11) NOT NULL,
  `userID` int(11) NOT NULL,
  `targetType` tinyint(4) NOT NULL COMMENT '0=全部 1=タグ(キャラ含む) 2=絵師',
  `targetID` int(11) DEFAULT NULL COMMENT '通知対象のID',
  `targetMethod` tinyint(4) NOT NULL DEFAULT '0' COMMENT '0=OneSignal 1=LINE 2=Twitter'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_ranking` (
  `rankingID` int(11) NOT NULL,
  `rankingYear` smallint(4) NOT NULL,
  `rankingMonth` tinyint(2) NOT NULL,
  `rankingDay` tinyint(2) NOT NULL,
  `rankingDayOfWeek` tinyint(1) NOT NULL,
  `illustID` int(11) NOT NULL,
  `illustLike` int(11) NOT NULL DEFAULT '0',
  `illustView` int(11) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_replace` (
  `replaceID` int(11) NOT NULL,
  `illustReplaceDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `illustGreaterID` int(11) NOT NULL,
  `illustLowerID` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_tag` (
  `illustID` int(11) NOT NULL,
  `tagID` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_upload` (
  `uploadID` int(11) NOT NULL,
  `uploadStartedDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `uploadFinishedDate` timestamp NULL DEFAULT NULL,
  `uploadStatus` tinyint(4) NOT NULL COMMENT '1=処理開始,2=Thumb作成,3=Large作成,4=Small作成,8=画像重複,5=終了,9=鯖爆発',
  `userID` int(11) NOT NULL,
  `illustID` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_user` (
  `userID` int(11) NOT NULL,
  `userDisplayID` varchar(20) DEFAULT NULL,
  `userTwitterID` varchar(20) DEFAULT NULL,
  `userLineID` varchar(50) DEFAULT NULL,
  `userOneSignalID` varchar(184) DEFAULT NULL COMMENT '5デバイスまでカンマ区切り',
  `userLineToken` varchar(100) DEFAULT NULL,
  `userName` varchar(20) DEFAULT NULL,
  `userPassword` varchar(100) DEFAULT NULL,
  `userFavorite` smallint(6) DEFAULT '42',
  `userTheme` tinyint(4) DEFAULT '0',
  `userPermission` tinyint(4) DEFAULT '0',
  `userApiSeq` int(11) DEFAULT '0',
  `userApiKey` varchar(300) DEFAULT NULL,
  `userInviteEnabled` tinyint(1) NOT NULL DEFAULT '1',
  `userToyApiKey` varchar(300) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_view` (
  `viewHistoryID` int(11) NOT NULL,
  `userID` int(11) NOT NULL,
  `illustID` int(11) NOT NULL,
  `last_view` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `data_wiki` (
  `articleID` int(11) NOT NULL,
  `articleTitle` varchar(50) NOT NULL,
  `articleBody` varchar(3000) NOT NULL,
  `targetType` int(11) NOT NULL COMMENT '0=ユーザー, 1=タグ, 2=絵師',
  `targetID` int(11) NOT NULL,
  `revision` int(11) NOT NULL,
  `createdTime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `userID` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `info_artist` (
  `artistID` int(11) NOT NULL,
  `userID` int(11) DEFAULT NULL,
  `artistName` varchar(50) NOT NULL,
  `artistDescription` varchar(200) DEFAULT NULL,
  `groupName` varchar(50) DEFAULT NULL,
  `pixivID` varchar(20) DEFAULT NULL,
  `twitterID` varchar(20) DEFAULT NULL,
  `mastodon` varchar(50) DEFAULT NULL,
  `homepage` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `info_mylist` (
  `mylistID` int(11) NOT NULL,
  `userID` int(11) DEFAULT NULL,
  `mylistName` varchar(30) DEFAULT NULL,
  `mylistDescription` varchar(300) DEFAULT NULL,
  `mylistCreatedDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `mylistUpdatedDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `mylistStatus` tinyint(4) DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `info_tag` (
  `tagID` int(11) NOT NULL,
  `userID` int(11) DEFAULT NULL,
  `tagType` tinyint(4) DEFAULT NULL COMMENT '0=タグ,1=キャラ,2=グループ,3=システム',
  `tagName` varchar(50) DEFAULT NULL,
  `tagDescription` varchar(200) DEFAULT NULL,
  `tagNsfw` tinyint(1) DEFAULT '0',
  `tagGroupID` int(11) DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
