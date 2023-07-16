/*
 Navicat Premium Data Transfer

 Source Server         : tencent_mysql
 Source Server Type    : MySQL
 Source Server Version : 50718
 Source Host           : gz-cynosdbmysql-grp-9fpcr503.sql.tencentcdb.com:23495
 Source Schema         : ps

 Target Server Type    : MySQL
 Target Server Version : 50718
 File Encoding         : 65001

 Date: 16/07/2023 19:11:37
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for datas
-- ----------------------------
DROP TABLE IF EXISTS `datas`;
CREATE TABLE `datas`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uname` varchar(64) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `name` varchar(64) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `create_time` datetime NOT NULL,
  `chart_data` json NOT NULL,
  `video_url` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 21 CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(64) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `password` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
