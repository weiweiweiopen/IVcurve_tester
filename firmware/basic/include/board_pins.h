#pragma once
#include <stddef.h>
namespace Pins {
constexpr int MUX_A[] = {2, 6, 4, 5}; // A0 bit 0 ... A3 bit 3
constexpr int EN=14, SDA=8, SCL=9, BUTTON=35;
constexpr int SCK=36, MISO=18, MOSI=16, CS=37, DC=38, RESET=-1, BUSY=-1, SRAM=34;
constexpr int used[]={2,6,4,5,14,8,9,35,36,18,16,37,38,34};
constexpr bool legal(int p) {
 return p==2||p==4||p==5||p==6||p==7||p==8||p==9||p==10||p==14||p==16||p==18||p==34||p==35||p==36||p==37||p==38;
}
constexpr bool distinct(size_t i=0,size_t j=1) {
 return i>=sizeof(used)/sizeof(*used) ? true :
   (!legal(used[i]) ? false : (j>=sizeof(used)/sizeof(*used) ? distinct(i+1,i+2) : (used[i]!=used[j] && distinct(i,j+1))));
}
static_assert(distinct(), "GPIO collision / reserved pin");
}
