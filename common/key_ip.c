/*
 * Additional data structures to track ip addresses in the config
 * Modified from key_value.c
 */

#include<stdio.h>
#include<stdlib.h>
#include"key_ip.h"

/* Function definition */
void key_ip_init();
int  key_ip_insert( int key, char *data );
int  key_ip_delete( int key );
int  key_ip_get   ( int key, char **data );

/* Element structure */

typedef struct element {
    int key;
    char *data;
    struct element *next;
} element;

int size_key_ip;
element start_key_ip;

/* Initialization */
void key_ip_init(){
    start_key_ip.key = -1;
    start_key_ip.data = NULL;
    start_key_ip.next = NULL;
    size_key_ip = 0;
}

/* Returns 1 if element is inserted, 0 if not, -1 if error */
int key_ip_insert( int key, char *data ){
	element *pelement, *velement;
	pelement = &start_key_ip;

	/*loop through looking for element. Stops when at spot to be inserted */
	while(pelement->next != NULL && pelement->next->key <=key){
		if(pelement->next->key == key) return 0;
		pelement = pelement->next;
	}
	
	/*insert element */
	velement = malloc(sizeof(element));
	if(velement == NULL) return -1;
	velement->key = key;
	velement->data = data;
	velement->next = pelement->next;
	pelement->next = velement;
	size_key_ip++;
	return 1;
}

/*return 1 if element is deleted, 0 if not, -1 if error */
int  key_ip_delete( int key ){
	element *pelement, *telement;
	pelement = &start_key_ip;
	/*loop thru looking for element. If there, deletes, if not exit */
	while(pelement->next != NULL && pelement->next->key <= key){
		if(pelement->next->key == key){
			telement = pelement->next;
			pelement->next = telement->next;
            free(telement->data); // free the string instance stored in heap
			free(telement);
			size_key_ip--;
			return 1;
		}
		pelement = pelement->next;
	}
	return 0;
}

/* Return 1 if element is in list, 0 if not */
int  key_ip_get   ( int key, char **data ){
	element *pelement;
	pelement = &start_key_ip;
	/*loop thru looking for element. IF found make *data point to data found */
	while(pelement != NULL && pelement->key <= key){
		if(pelement->key == key){
			*data = pelement->data;
			return 1;
		}
		pelement = pelement->next;
	}
	return 0;
}
