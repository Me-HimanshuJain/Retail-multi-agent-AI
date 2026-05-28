library(data.table)
library(plyr)
library(forecast)

round <- "evaluation" #validation" 

#Import data
if (round=="evaluation"){
  #Train and test set for the private leaderboard - evaluation phase
  train_set <- fread("sales_train_evaluation.csv")
  test_set <- fread("sales_test_evaluation.csv")
  weights <- fread("weights_evaluation.csv")
}else{
  #Train and test set for the public leaderboard - validation phase
  train_set <- fread("sales_train_validation.csv")
  test_set <- fread("sales_test_validation.csv")
  weights <- fread("weights_validation.csv")
}

#Dummy submission (Naive forecasts)
base_forecasts <- NULL
weights$RMSSE <- NA
for (tsid in 1:nrow(weights)){
  
  if (weights$Level_id[tsid]=="Level12"){
    
    insample <- as.numeric(train_set[train_set$item_id==weights$Agg_Level_1[tsid] & 
                                       train_set$store_id==weights$Agg_Level_2[tsid],6:ncol(train_set)])
    
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
    frc <- as.numeric(naive(insample, h=28)$mean) #Produce forecasts
    
    tmp <- test_set[test_set$item_id==weights$Agg_Level_1[tsid] & 
                      test_set$store_id==weights$Agg_Level_2[tsid],]
    outsample <- as.numeric(tmp[,6:ncol(test_set)]) # Test set
    
    base_forecasts <- rbind(base_forecasts, cbind(tmp[,1:5], t(frc))) #Store base forecasts
    
  }else if (weights$Level_id[tsid]=="Level11"){
    
    insample <- train_set[train_set$item_id==weights$Agg_Level_2[tsid] & 
                            train_set$state_id==weights$Agg_Level_1[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$item_id==weights$Agg_Level_2[tsid] & 
                            test_set$state_id==weights$Agg_Level_1[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$item_id==weights$Agg_Level_2[tsid] & 
                            base_forecasts$state_id==weights$Agg_Level_1[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level10"){
    
    insample <- train_set[train_set$item_id==weights$Agg_Level_1[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$item_id==weights$Agg_Level_1[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$item_id==weights$Agg_Level_1[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level9"){
    
    insample <- train_set[train_set$store_id==weights$Agg_Level_1[tsid] & 
                            train_set$dept_id==weights$Agg_Level_2[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$store_id==weights$Agg_Level_1[tsid] & 
                            test_set$dept_id==weights$Agg_Level_2[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$store_id==weights$Agg_Level_1[tsid] & 
                            base_forecasts$dept_id==weights$Agg_Level_2[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level8"){
    
    insample <- train_set[train_set$store_id==weights$Agg_Level_1[tsid] & 
                            train_set$cat_id==weights$Agg_Level_2[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$store_id==weights$Agg_Level_1[tsid] & 
                            test_set$cat_id==weights$Agg_Level_2[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$store_id==weights$Agg_Level_1[tsid] & 
                            base_forecasts$cat_id==weights$Agg_Level_2[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level7"){
    
    insample <- train_set[train_set$state_id==weights$Agg_Level_1[tsid] & 
                            train_set$dept_id==weights$Agg_Level_2[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$state_id==weights$Agg_Level_1[tsid] & 
                            test_set$dept_id==weights$Agg_Level_2[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$state_id==weights$Agg_Level_1[tsid] & 
                            base_forecasts$dept_id==weights$Agg_Level_2[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level6"){
    
    insample <- train_set[train_set$state_id==weights$Agg_Level_1[tsid] & 
                            train_set$cat_id==weights$Agg_Level_2[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$state_id==weights$Agg_Level_1[tsid] & 
                            test_set$cat_id==weights$Agg_Level_2[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$state_id==weights$Agg_Level_1[tsid] & 
                            base_forecasts$cat_id==weights$Agg_Level_2[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level5"){
    
    insample <- train_set[train_set$dept_id==weights$Agg_Level_1[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$dept_id==weights$Agg_Level_1[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$dept_id==weights$Agg_Level_1[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level4"){
    
    insample <- train_set[train_set$cat_id==weights$Agg_Level_1[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$cat_id==weights$Agg_Level_1[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$cat_id==weights$Agg_Level_1[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level3"){
    
    insample <- train_set[train_set$store_id==weights$Agg_Level_1[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$store_id==weights$Agg_Level_1[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$store_id==weights$Agg_Level_1[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level2"){
    
    insample <- train_set[train_set$state_id==weights$Agg_Level_1[tsid],6:ncol(train_set)]
    outsample <- test_set[test_set$state_id==weights$Agg_Level_1[tsid],6:ncol(test_set)]
    frc <- base_forecasts[base_forecasts$state_id==weights$Agg_Level_1[tsid],6:ncol(base_forecasts)]
    
    insample <- as.numeric(colSums(insample))
    outsample <- as.numeric(colSums(outsample))
    frc <- as.numeric(colSums(frc))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }else if (weights$Level_id[tsid]=="Level1"){
    
    insample <- as.numeric(colSums(train_set[,6:ncol(train_set)]))
    outsample <- as.numeric(colSums(test_set[,6:ncol(test_set)]))
    frc <- as.numeric(colSums(base_forecasts[,6:ncol(base_forecasts)]))
    tmp <- data.frame(insample,c(1:length(insample))) #Find first non-zero demand
    start <- head(tmp[tmp$insample>0,2],1)
    insample <- insample[start:length(insample)]
    
  }
  
  
  weights$RMSSE[tsid] <- sqrt(mean((frc-outsample)^2)/mean(diff(insample)^2)) #Estimate error
  
}

weights$WRMSSE <- weights$RMSSE*weights$weight

WRMSSE_per_level <- c(weights[weights$Level_id=="Level1",]$WRMSSE,
                      sum(weights[weights$Level_id=="Level2",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level3",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level4",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level5",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level6",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level7",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level8",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level9",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level10",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level11",]$WRMSSE),
                      sum(weights[weights$Level_id=="Level12",]$WRMSSE))
mean(WRMSSE_per_level)
