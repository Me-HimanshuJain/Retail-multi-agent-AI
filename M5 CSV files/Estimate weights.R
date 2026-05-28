library(data.table)
library(plyr)

round <- "evaluation" #"validation"

#Import data
if (round=="evaluation"){
  #Train set for the private leaderboard - evaluation phase
  train_set <- fread("sales_train_evaluation.csv")
}else{
  #Train set for the public leaderboard - validation phase
  train_set <- fread("sales_train_validation.csv")
}
calendar <- fread("calendar.csv")
prices <- fread("sell_prices.csv")

# Estimate weights
weights_tot <- NULL
#Level 12
weights <- data.frame(matrix(NA, nrow = nrow(train_set), ncol = 9))
colnames(weights) <- c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales",
                       "item_id","dept_id","cat_id","store_id","state_id")
weights$Level_id <- "Level12"
for (tsid in 1:nrow(train_set)){
  temp <- train_set[tsid,]
  train_temp <- calendar[1:(ncol(temp)-5),c("date","wm_yr_wk")]
  prices_train <- prices[(prices$store_id==temp$store_id) & (prices$item_id==temp$item_id),]
  train_temp <- merge(train_temp, prices_train, all.x = T)
  train_temp$quantity <- as.numeric(temp[,6:ncol(temp)])
  train_temp <- tail(train_temp,28)
  dollar_sales <- sum(train_temp$sell_price*train_temp$quantity)
  weights$Agg_Level_1[tsid] = weights$item_id[tsid] <- temp$item_id
  weights$Agg_Level_2[tsid] = weights$store_id[tsid] <- temp$store_id
  weights$Dollar_Sales[tsid] <- dollar_sales
  weights$cat_id[tsid] <- temp$cat_id
  weights$state_id[tsid] <- temp$state_id
  weights$dept_id[tsid] <- temp$dept_id
}
weights_tot <- rbind(weights_tot, weights[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")])

#Level 11
temp <- ddply(weights[c("state_id","item_id","Dollar_Sales")], .(state_id,item_id), colwise(sum))
temp$Level_id <- "Level11"
colnames(temp) <- c("Agg_Level_1","Agg_Level_2","Dollar_Sales","Level_id")
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 10
temp <- ddply(weights[c("item_id","Dollar_Sales")], .(item_id), colwise(sum))
temp$Level_id <- "Level10"
colnames(temp) <- c("Agg_Level_1","Dollar_Sales","Level_id")
temp$Agg_Level_2 <- "X"
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 9
temp <- ddply(weights[c("store_id","dept_id","Dollar_Sales")], .(store_id,dept_id), colwise(sum))
temp$Level_id <- "Level9"
colnames(temp) <- c("Agg_Level_1","Agg_Level_2","Dollar_Sales","Level_id")
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 8
temp <- ddply(weights[c("store_id","cat_id","Dollar_Sales")], .(store_id,cat_id), colwise(sum))
temp$Level_id <- "Level8"
colnames(temp) <- c("Agg_Level_1","Agg_Level_2","Dollar_Sales","Level_id")
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 7
temp <- ddply(weights[c("state_id","dept_id","Dollar_Sales")], .(state_id,dept_id), colwise(sum))
temp$Level_id <- "Level7"
colnames(temp) <- c("Agg_Level_1","Agg_Level_2","Dollar_Sales","Level_id")
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 6
temp <- ddply(weights[c("state_id","cat_id","Dollar_Sales")], .(state_id,cat_id), colwise(sum))
temp$Level_id <- "Level6"
colnames(temp) <- c("Agg_Level_1","Agg_Level_2","Dollar_Sales","Level_id")
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 5
temp <- ddply(weights[c("dept_id","Dollar_Sales")], .(dept_id), colwise(sum))
temp$Level_id <- "Level5"
colnames(temp) <- c("Agg_Level_1","Dollar_Sales","Level_id")
temp$Agg_Level_2 <- "X"
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 4
temp <- ddply(weights[c("cat_id","Dollar_Sales")], .(cat_id), colwise(sum))
temp$Level_id <- "Level4"
colnames(temp) <- c("Agg_Level_1","Dollar_Sales","Level_id")
temp$Agg_Level_2 <- "X"
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 3
temp <- ddply(weights[c("store_id","Dollar_Sales")], .(store_id), colwise(sum))
temp$Level_id <- "Level3"
colnames(temp) <- c("Agg_Level_1","Dollar_Sales","Level_id")
temp$Agg_Level_2 <- "X"
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 2
temp <- ddply(weights[c("state_id","Dollar_Sales")], .(state_id), colwise(sum))
temp$Level_id <- "Level2"
colnames(temp) <- c("Agg_Level_1","Dollar_Sales","Level_id")
temp$Agg_Level_2 <- "X"
temp <- temp[,c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")]
weights_tot <- rbind(weights_tot,temp)

#Level 1
temp <- data.frame("Level1","Total","X",sum(weights$Dollar_Sales))
colnames(temp) <- c("Level_id","Agg_Level_1","Agg_Level_2","Dollar_Sales")
weights_tot <- rbind(weights_tot,temp)

weights_tot$weight <- round(weights_tot$Dollar_Sales*12/sum(weights_tot$Dollar_Sales),12)

write.csv(weights_tot, paste0("weights_",round,".csv"), row.names = F)