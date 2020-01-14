var currentCid = 1; // 当前分类 id
var cur_page = 1; // 当前页
var total_page = 1;  // 总页数
var data_querying = true;   // 是否正在向后台获取数据


$(function () {
    // 当我们加载页面的时候，需要更新数据
    updateNewsData()
    // 首页分类切换
    $('.menu li').click(function () {
        var clickCid = $(this).attr('data-cid')
        $('.menu li').each(function () {
            $(this).removeClass('active')
        })
        $(this).addClass('active')

        if (clickCid != currentCid) {
            // 记录当前分类id
            currentCid = clickCid

            // 重置分页参数
            cur_page = 1
            total_page = 1
            updateNewsData()
        }
    })

    //页面滚动加载相关
    $(window).scroll(function () {

        // 浏览器窗口高度
        var showHeight = $(window).height();

        // 整个网页的高度
        var pageHeight = $(document).height();

        // 页面可以滚动的距离
        var canScrollHeight = pageHeight - showHeight;

        // 页面滚动了多少,这个是随着页面滚动实时变化的
        var nowScroll = $(document).scrollTop();

        if ((canScrollHeight - nowScroll) < 100) {
            // 判断页数，去更新新闻数据
            // 当屏幕滚到底部的时候，并且还没有向后台请求数据
            if (!data_querying){
                // 设置正在请求数据
                data_querying = true
                // 如果没到最后一页，就加载数据
                if (cur_page < total_page){
                    updateNewsData()
                }else {
                    // 如果当前页已经到达最后一页了，那么我们就不去加载数据了
                    data_querying = false
                }
            }
        }
    })
})

function updateNewsData() {
    // 更新新闻数据
    var params = {
        "page": cur_page,
        "cid": currentCid
    }
    $.get("/news_list", params, function (resp) {
        // 当我向后台请求数据的时候，我就不加载数据了
        data_querying = false
        if (resp.errno == "0"){
            // 数据加载成功
            total_page = resp.data.total_page
            // 1、当当前页为第一页的时候， 清空ul下面的内容
            if (cur_page == 1){
                $(".list_con").html("")
            }
            // 这个时候将当前页 += 1 为第二次做准备
            cur_page += 1
            // 2、然后添加我们返回的数据
            for (var i=0;i<resp.data.news_list.length;i++) {
                var news = resp.data.news_list[i]
                var content = '<li>'
                content += '<a href="/news/'+ news.id +'" class="news_pic fl"><img src="' + news.index_image_url + '?imageView2/1/w/170/h/170"></a>'
                content += '<a href="/news/'+ news.id +'" class="news_title fl">' + news.title + '</a>'
                content += '<a href="/news/'+ news.id +'" class="news_detail fl">' + news.digest + '</a>'
                content += '<div class="author_info fl">'
                content += '<div class="source fl">来源：' + news.source + '</div>'
                content += '<div class="time fl">' + news.create_time + '</div>'
                content += '</div>'
                content += '</li>'
                $(".list_con").append(content)
            }
        }else{
            // 数据加载失败
            alert(resp.errmsg)
        }
    })
}
