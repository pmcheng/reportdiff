# analysis.R

# generate plots and analysis for ReportDiff

library(RSQLite)
library(ggplot2)
library(dplyr)
library(lubridate)
drv = dbDriver("SQLite")


pw=10
ph=7.5

# adjust paths here
setwd("~/Radiology USC/reportdiff/core/analysis")
path_reportdb="../powerscribe/reportdiff_ps.db"
path_usersdb="../powerscribe/users.db"
ifelse(!dir.exists(file.path("png","anon")), dir.create(file.path("png","anon"),recursive=TRUE), FALSE)
ifelse(!dir.exists(file.path("pdf","anon")), dir.create(file.path("pdf","anon"),recursive=TRUE), FALSE)


heatmap.f=function(study_data,plot_title,sortbymean=FALSE,sortbysd=FALSE) {
  # Generate heatmap from study data.
  
  # Args:
  #   study_data: data frame with columns for attending, resident, diff_score_percent
  #   plot_title: string for ggplot title
  #   
  #   sortbymean
  #   sortbysd
  #
  # Returns:
  #   ggplot heatmap (geom_tile)
  dfp=study_data %>% group_by(attending,resident) %>% summarize(diff_score_percent = mean(diff_score_percent))
  
  if (sortbymean) {
    ordered_residents=(dfp %>% group_by(resident) 
                       %>% summarize(avscore = mean(diff_score_percent)) 
                       %>% arrange(desc(avscore)))[["resident"]]
    
    dfp$resident=factor(dfp$resident,levels=ordered_residents)
    
    ordered_attendings=(dfp %>% group_by(attending) 
                        %>% summarize(avscore = mean(diff_score_percent)) 
                        %>% arrange(desc(avscore)))[["attending"]]
    
    dfp$attending=factor(dfp$attending,levels=ordered_attendings)
    
  } else if (sortbysd) {
    adj_data= (study_data %>% group_by(attending) 
               %>% mutate(adjdiff=(diff_score_percent-mean(diff_score_percent))))
    
    ordered_residents=(adj_data %>% group_by(resident) 
                       %>% summarize(rankscore = mean(adjdiff)) 
                       %>% arrange(desc(rankscore)))[["resident"]]
    
    dfp$resident=factor(dfp$resident,levels=ordered_residents)
    
    # ordered_attendings=(study_data %>% group_by(attending) %>% summarize(sdscore = sd(diff_score_percent)) %>%arrange(desc(sdscore)))[["attending"]]
    
    ordered_attendings=(dfp %>% group_by(attending) 
                        %>% summarize(avscore = mean(diff_score_percent)) 
                        %>% arrange(desc(avscore)))[["attending"]]
    
    dfp$attending=factor(dfp$attending,levels=ordered_attendings)
    
  }
  
  heatmap=ggplot(dfp,aes(x=resident, y=attending, fill=sqrt(diff_score_percent)))+
    geom_tile()+
    scale_fill_gradient(name="Edit",low="yellow", high="red")+
    theme(axis.text.x = element_text(angle = 90,hjust=1,vjust=0.5))+
    scale_y_discrete('Attending')+
    scale_x_discrete('Trainee') +
    ggtitle(sprintf("%s, %s to %s (n=%i)",plot_title, substr(min(study_data$prelim_timestamp),1,10),substr(max(study_data$prelim_timestamp),1,10),nrow(study_data)))
  
  ggsave (paste("pdf/",plot_title,".pdf",sep=''),heatmap,width=pw,height=ph)
  ggsave (paste("png/",plot_title,".png",sep=''),heatmap,width=pw,height=ph)
  
  heatmap=heatmap+theme(axis.text.x = element_blank(), axis.text.y = element_blank())
  ggsave (paste("pdf/anon/",plot_title,".pdf",sep=''),heatmap,width=pw,height=ph)
  ggsave (paste("png/anon/",plot_title,".png",sep=''),heatmap,width=pw,height=ph)
  
  return(heatmap)
}


con = dbConnect(drv, path_reportdb)

dbGetQuery(con, paste("attach '",path_usersdb,"' as users",sep=''))

study_data=dbGetQuery(con,"select proceduredescription, prelim_timestamp, modality, resident, attending, attendingID, diff_score, diff_score_percent, grad_date from study, users where diff_score is not NULL and residentID is not NULL and study.residentID=users.ps_id")

dbDisconnect(con)


# At USC we have two Dr. Kevin King's in radiology!  Whose idea was that?  We must disambiguate...

study_data$attending[study_data$attendingID=='395']="Kevin G. King"
study_data$attending[study_data$attendingID=='553']="Kevin S. King"



p=heatmap.f(study_data,"All edits ordered by full name")  
p=heatmap.f(study_data,"All edits ordered by mean",sortbymean=TRUE)  
p=heatmap.f(study_data,"All edits ordered by adjusted mean",sortbysd=TRUE)  

for (yr in 2016:2019) {
  my_subset=study_data%>% filter(grad_date==yr)
  if (nrow(my_subset)>1) {
    p=heatmap.f(my_subset,paste("Class of",yr,"edits ordered by full name"))
    p=heatmap.f(my_subset,paste("Class of",yr,"edits ordered by mean"),sortbymean=TRUE)  
    p=heatmap.f(my_subset,paste("Class of",yr,"edits ordered by adjusted mean"),sortbysd=TRUE)  
  }
}

my_subset=study_data%>% filter(modality=="CT")
p=heatmap.f(my_subset,"CT edits ordered by mean",sortbymean=TRUE)  
p=heatmap.f(my_subset,"CT edits ordered by adjusted mean",sortbysd=TRUE)  

my_subset=study_data%>% filter(modality=="MR")
p=heatmap.f(my_subset,"MR edits ordered by mean",sortbymean=TRUE)  
p=heatmap.f(my_subset,"MR edits ordered by adjusted mean",sortbysd=TRUE)  

my_subset=study_data%>% filter(modality=="US")
p=heatmap.f(my_subset,"US edits ordered by mean",sortbymean=TRUE)  
p=heatmap.f(my_subset,"US edits ordered by adjusted mean",sortbysd=TRUE)  


my_subset=study_data #  %>% filter(grad_date>=2015) %>% filter(modality!="RA")   
p=ggplot(my_subset,aes(x=modality,y=diff_score_percent))+
  stat_summary(fun.y=mean,geom="bar")+
  ggtitle(sprintf("Edit score by modality %s to %s (n=%i)", substr(min(my_subset$prelim_timestamp),1,10),substr(max(my_subset$prelim_timestamp),1,10),nrow(my_subset)))+
  scale_y_continuous('Edit score %')
ggsave ("pdf/Edit Score by Modality.pdf",p,width=pw,height=ph)
ggsave ("png/Edit Score by Modality.png",p,width=pw,height=ph)



adj_data= study_data %>% filter(grad_date>=2015)%>% group_by(attending) %>% mutate(adjdiff=(diff_score_percent-mean(diff_score_percent)))
adj_data= adj_data %>% group_by(resident,grad_date) %>% summarize(count=n(),rankscore=mean(adjdiff))%>%ungroup()
ordered_residents=as.vector(adj_data %>% arrange(desc(rankscore)))[["resident"]]
adj_data$resident=factor(adj_data$resident,levels=ordered_residents)

p=ggplot(adj_data,aes(x=resident,y=rankscore))+
  geom_bar(stat="identity",aes(fill=factor(grad_date)))+
  theme(axis.text.x = element_text(size=5, angle = 90,hjust=1))+
  guides(fill=guide_legend(title="Class"))+
  scale_y_continuous('Average mean-centered edit score %')+
  ggtitle("Average mean-centered diff percent")

ggsave ("pdf/Mean-centered diff percent.pdf",p,width=pw,height=ph)
ggsave ("png/Mean-centered diff percent.png",p,width=pw,height=ph)
p=p+theme(axis.text.x = element_blank())    
ggsave ("pdf/anon/Mean-centered diff percent.pdf",p,width=pw,height=ph)
ggsave ("png/anon/Mean-centered diff percent.png",p,width=pw,height=ph)

p=ggplot(adj_data,aes(x=resident,y=count))+
  geom_bar(stat="identity",aes(fill=factor(grad_date)))+
  theme(axis.text.x = element_text(size=5, angle = 90,hjust=1))+
  guides(fill=guide_legend(title="Class"))+
  ggtitle("Number of Dictated Studies vs. Average Edit Score")
ggsave ("pdf/Count.pdf",p,width=pw,height=ph)
ggsave ("png/Count.png",p,width=pw,height=ph)
p=p+theme(axis.text.x = element_blank())    
ggsave ("pdf/anon/Count.pdf",p,width=pw,height=ph)
ggsave ("png/anon/Count.png",p,width=pw,height=ph)



p=ggplot(adj_data,aes(x=rankscore,y=count))+
  geom_point(shape=1)+
  geom_vline(xintercept=0,color="red")+
  ggtitle("Mean-centered diff percent vs. Count")
ggsave ("pdf/Mean-centered diff percent vs Count.pdf",p,width=pw,height=ph)
ggsave ("png/Mean-centered diff percent vs Count.png",p,width=pw,height=ph)

time_data=study_data %>% filter(grad_date!="") %>% mutate(exp=(as.period(years(4)+ymd_hms(prelim_timestamp)-ymd(paste(grad_date,"-07-01")),units="months"))/months(1)) %>% filter(exp<48 & diff_score_percent<100)

p=ggplot(time_data,aes(exp,diff_score_percent)) +
  geom_point(aes(color=modality))+
  ggtitle(sprintf("Edit score vs. Training Time %s to %s (n=%i)", substr(min(time_data$prelim_timestamp),1,10),substr(max(time_data$prelim_timestamp),1,10),nrow(time_data)))+
  scale_x_continuous('Training (months)')+
  scale_y_continuous('Edit score %')
ggsave ("pdf/Training Time.pdf",p,width=pw,height=ph)
ggsave ("png/Training Time.png",p,width=pw,height=ph)

p=ggplot(time_data,aes(factor(round(exp)),diff_score_percent)) +
  geom_boxplot()+
  ggtitle(sprintf("Edit score vs. Training Time %s to %s (n=%i)", substr(min(time_data$prelim_timestamp),1,10),substr(max(time_data$prelim_timestamp),1,10),nrow(time_data)))+
  scale_x_discrete('Training (months)')+
  scale_y_continuous('Edit score %')
ggsave ("pdf/Training Time Boxplot.pdf",p,width=pw,height=ph)
ggsave ("png/Training Time Boxplot.png",p,width=pw,height=ph)
