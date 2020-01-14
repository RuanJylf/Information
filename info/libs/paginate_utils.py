from flask import current_app, g

from info import user_login
from info.models import News


class PaginateManage(object):

    @classmethod
    def _paginate(cls, page, query, per_page=10, filters=list(), order_bys=list()):
        try:
            page = int(page)
        except Exception as e:
            current_app.logger.error(e)

        news_li = []
        total_page = 1
        current_page = 1
        try:
            paginate = query.filter(*filters).order_by(*order_bys).paginate(page, per_page, False)
            news_li = paginate.items
            total_page = paginate.pages
            current_page = paginate.page
        except Exception as e:
            current_app.logger.error(e)

        news_dict_li = [news.to_dict() for news in news_li]

        data = {
            "news_list": news_dict_li,
            "total_page": total_page,
            "current_page": current_page
        }

        return data

    @classmethod
    def index_paginate(cls, page, cid):
        """
        首页新闻的分页逻辑
        :param page:
        :param cid:
        :return:
        """
        try:
            cid = int(cid)
        except Exception as e:
            current_app.logger.error(e)
        filters = [News.status == 0]
        if cid != 1:
            filters.append(News.category_id == cid)
        order_bys = [News.create_time.desc()]
        query = News.query
        data = cls._paginate(page, query, filters=filters, order_bys=order_bys)
        return data

    @classmethod
    @user_login
    def news_collection_paginate(cls, page):
        query = g.user.collection_news
        data = cls._paginate(page, query)
        return data



    @classmethod
    @user_login
    def news_list_paginate(cls, page):
        filters = [News.user_id == g.user.id]
        order_bys = [News.create_time.desc()]
        query = News.query
        data = cls._paginate(page, query, filters=filters, order_bys=order_bys)
        return data
